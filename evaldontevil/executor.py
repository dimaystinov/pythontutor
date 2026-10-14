"""Fail-closed client for the separately deployed container runner."""
import json
import os
import urllib.error
import urllib.request


class ExecuteResult:
    def __init__(self, payload=None):
        payload = payload or {}
        self.result = payload.get('result', 'internal_error')
        self.stdout = payload.get('stdout', '')
        self.stderr = payload.get('stderr', '')
        self.exception = payload.get('exception')
        if 'image' in payload:
            self.image = payload['image']
        if 'trace' in payload:
            self.trace = payload['trace']


def execute_python(code, stdin='', explain=False, image=None):
    if not isinstance(code, str) or not isinstance(stdin, str):
        return ExecuteResult()
    if len(code.encode()) > 65536 or len(stdin.encode()) > 65536:
        return ExecuteResult()
    url, token = os.getenv('RUNNER_URL'), os.getenv('RUNNER_TOKEN')
    if not url or not token:
        return ExecuteResult()
    request = urllib.request.Request(url.rstrip('/') + '/execute',
        data=json.dumps({'code': code, 'stdin': stdin, 'explain': bool(explain) if image is None else False, 'image': image}).encode(),
        headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token})
    try:
        # Do not send the internal authentication token through environment proxies.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(request, timeout=20) as response:
            raw = response.read(8 * 1024 * 1024 + 1)
        if len(raw) > 8 * 1024 * 1024:
            return ExecuteResult()
        payload = json.loads(raw)
        if not isinstance(payload, dict) or not isinstance(payload.get('stdout'), str):
            return ExecuteResult()
        return ExecuteResult(payload)
    except (OSError, ValueError, RecursionError, urllib.error.URLError):
        return ExecuteResult()
