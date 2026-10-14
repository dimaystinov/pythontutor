"""Authenticated control plane: the only component with Docker socket access."""
import hmac
import json
import os
import selectors
import subprocess
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from runner.images import InvalidImage, decode_image, encode_image

MAX_RESPONSE = 8 * 1024 * 1024
MAX_REQUEST = 4 * 1024 * 1024
SLOTS = threading.BoundedSemaphore(4)


def failure(kind='internal_error'):
    return {'result': kind, 'stdout': '', 'stderr': '', 'exception': None}


def valid_payload(payload):
    if not isinstance(payload, dict) or payload.get('result') not in {
        'ok', 'stderr', 'unhandled_exception', 'instructions_limited', 'output_limited', 'invalid_image'}:
        return False
    if not all(isinstance(payload.get(k), str) for k in ('stdout', 'stderr')):
        return False
    error = payload.get('exception')
    if error is not None and (not isinstance(error, dict) or not isinstance(error.get('line'), int)
            or not all(isinstance(error.get(k), str) for k in ('exception_type', 'exception_msg'))):
        return False
    trace = payload.get('trace', [])
    return isinstance(trace, list) and len(trace) <= 1002 and all(
        isinstance(entry, dict) and entry.get('event') in {
            'call', 'step_line', 'return', 'exception', 'uncaught_exception', 'instruction_limit_reached'}
        for entry in trace)


def docker_command(name):
    return ['docker', 'run', '--rm', '--pull=never', '--name', name,
        '--label', 'pythontutor.job=true', '--network=none', '--user=65534:65534',
        '--read-only', '--cap-drop=ALL', '--security-opt=no-new-privileges',
        '--memory=512m', '--memory-swap=512m', '--cpus=1', '--pids-limit=32',
        '--ulimit', 'cpu=10:10', '--ulimit', 'nofile=64:64', '--ulimit', 'fsize=4194304:4194304',
        '--tmpfs', '/tmp:rw,noexec,nosuid,nodev,size=64m,mode=1777',
        '--log-driver=none', '-i', os.getenv('RUNNER_IMAGE', 'pythontutor-worker:local')]


def execute(request):
    name = 'pythontutor-job-' + uuid.uuid4().hex
    process = None
    selector = selectors.DefaultSelector()
    try:
        process = subprocess.Popen(docker_command(name), stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        def feed():
            try:
                process.stdin.write(json.dumps(request).encode())
                process.stdin.close()
            except (OSError, ValueError):
                pass
        threading.Thread(target=feed, daemon=True).start()
        selector.register(process.stdout, selectors.EVENT_READ, 'out')
        selector.register(process.stderr, selectors.EVENT_READ, 'err')
        buffers = {'out': bytearray(), 'err': bytearray()}
        deadline = time.monotonic() + 10
        while selector.get_map():
            if time.monotonic() > deadline:
                return failure('realtime_limited')
            for key, _ in selector.select(timeout=0.1):
                data = os.read(key.fileobj.fileno(), 65536)
                if not data:
                    selector.unregister(key.fileobj)
                else:
                    buffers[key.data].extend(data)
                    if sum(map(len, buffers.values())) > MAX_RESPONSE:
                        return failure('output_limited')
        status = process.wait(timeout=max(0.01, deadline-time.monotonic()))
        if status in (137, 152):
            return failure('realtime_limited')
        if status != 0 or buffers['err']:
            return failure()
        payload = json.loads(buffers['out'])
        if not valid_payload(payload):
            return failure()
        if 'image' in payload:
            try:
                payload['image'] = encode_image(decode_image(payload['image']))
            except InvalidImage:
                return failure('invalid_image')
        return payload
    except (OSError, ValueError, RecursionError, subprocess.SubprocessError):
        return failure()
    finally:
        selector.close()
        if process is not None:
            if process.poll() is None:
                process.kill()
            process.wait()
            for stream in (process.stdout, process.stderr):
                stream.close()
        # rm -f is necessary: killing the Docker client alone does not kill its container.
        try:
            subprocess.run(['docker', 'rm', '-f', name], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=3, check=False)
        except (OSError, subprocess.SubprocessError):
            pass


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def reply(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self.reply(200 if self.path == '/healthz' else 404, {'status': 'ok'})

    def do_POST(self):
        token = os.getenv('RUNNER_TOKEN', '')
        if len(token) < 32 or not hmac.compare_digest(self.headers.get('Authorization', '').encode(), ('Bearer ' + token).encode()):
            return self.reply(403, failure())
        if self.path != '/execute':
            return self.reply(404, failure())
        if not SLOTS.acquire(blocking=False):
            return self.reply(503, failure())
        try:
            self.execute_request()
        finally:
            SLOTS.release()

    def execute_request(self):
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if length < 1 or length > MAX_REQUEST:
                return self.reply(413, failure())
            request = json.loads(self.rfile.read(length))
            if not isinstance(request, dict):
                raise ValueError('object required')
            if any(not isinstance(request.get(k, ''), str) or len(request.get(k, '').encode()) > 65536 for k in ('code', 'stdin')):
                raise ValueError('invalid source')
            if type(request.get('explain', False)) is not bool:
                raise ValueError('invalid explain')
            image = request.get('image')
            if image is not None:
                image = encode_image(decode_image(image))
            request = {'code': request.get('code', ''), 'stdin': request.get('stdin', ''), 'explain': request.get('explain', False) if image is None else False, 'image': image}
        except InvalidImage:
            return self.reply(200, failure('invalid_image'))
        except (ValueError, RecursionError, OSError):
            return self.reply(400, failure())
        self.reply(200, execute(request))

    def log_message(self, format, *args):
        pass  # Never log learner source, credentials, or request contents.


if __name__ == '__main__':
    if len(os.getenv('RUNNER_TOKEN', '')) < 32:
        raise SystemExit('RUNNER_TOKEN must contain at least 32 characters')
    ThreadingHTTPServer(('0.0.0.0', 8081), Handler).serve_forever()
