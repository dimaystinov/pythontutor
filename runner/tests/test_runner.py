import json
import os
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from unittest.mock import patch

import pytest
from evaldontevil.executor import execute_python
from evaldontevil.execplainator import exec as trace_exec, simple_exec
from runner.server import Handler, docker_command, execute


def test_basic_and_errors():
    assert simple_exec('print(int(input()) + 2)', '40')['stdout'] == '42\n'
    for source, kind in [('if :', 'SyntaxError'), ('1/0', 'ZeroDivisionError'), ('raise Exception()', 'Exception')]:
        result = trace_exec(source)
        assert result['result'] == 'unhandled_exception'
        assert result['exception']['exception_type'] == kind
        assert result['trace'][-1]['event'] == 'uncaught_exception'
    assert trace_exec('try:\n 1/0\nexcept ZeroDivisionError:\n pass')['result'] == 'ok'


def test_recursive_and_circular_trace():
    result = trace_exec('a=[]\na.append(a)\ndef f(n):\n return n*f(n-1) if n else 1\nprint(f(4))')
    assert result['stdout'] == '24\n'
    assert any(len(e['stack_locals']) > 2 for e in result['trace'])
    assert 'CIRCULAR_REF' in json.dumps(result)
    assert result['trace'][-1]['globals']['a'][0] == 'LIST'


def test_limits():
    assert trace_exec('while True: pass')['result'] == 'instructions_limited'
    assert simple_exec('print("x" * 100000)')['result'] == 'output_limited'
    assert len(simple_exec('print("x" * 100000)')['stdout']) == 65536


def test_no_fallback(monkeypatch):
    monkeypatch.delenv('RUNNER_URL', raising=False)
    assert execute_python('raise Exception()').result == 'internal_error'
    monkeypatch.setenv('RUNNER_URL', 'http://127.0.0.1:1')
    monkeypatch.setenv('RUNNER_TOKEN', 'x'*32)
    assert execute_python('print(42)').result == 'internal_error'
    with patch('runner.server.subprocess.Popen', side_effect=FileNotFoundError):
        assert execute({'code': 'print(42)'})['result'] == 'internal_error'


def test_docker_hardening():
    command = docker_command('test-job')
    for flag in ['--network=none', '--read-only', '--cap-drop=ALL', '--security-opt=no-new-privileges',
                 '--user=65534:65534', '--memory=512m', '--memory-swap=512m', '--pids-limit=32']:
        assert flag in command
    assert '-v' not in command and '--privileged' not in command


def test_authenticated_http(monkeypatch):
    monkeypatch.setenv('RUNNER_TOKEN', 'a'*32)
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv('RUNNER_URL', f'http://127.0.0.1:{server.server_port}')
    try:
        request = urllib.request.Request(os.environ['RUNNER_URL']+'/execute', data=b'{}')
        with pytest.raises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(request)
        assert error.value.code == 403
        with patch('runner.server.execute', return_value={'result':'ok','stdout':'42\n','stderr':'','exception':None}):
            assert execute_python('print(42)').stdout == '42\n'
        invalid = urllib.request.Request(os.environ['RUNNER_URL']+'/execute', data=b'{"code":[]}', headers={'Authorization':'Bearer '+'a'*32})
        with pytest.raises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(invalid)
        assert error.value.code == 400
    finally:
        server.shutdown()
        server.server_close()


@pytest.mark.skipif(os.getenv('RUN_DOCKER_TESTS') != '1', reason='Requires built worker image and Docker')
def test_real_container_isolation():
    def run(code, explain=False):
        return execute({'code':code,'stdin':'','explain':explain})
    assert run('print(42)')['stdout'] == '42\n'
    assert run('a=[1,2]\nprint(a)', True)['trace'][-1]['globals']['a'][0] == 'LIST'
    result = run('import os\nprint(os.getuid())\nprint(os.path.exists("/var/run/docker.sock"))\nprint("RUNNER_TOKEN" in os.environ)')
    assert result['stdout'] == '65534\nFalse\nFalse\n'
    assert run('open("/app/host-write", "w")')['exception']['exception_type'] == 'OSError'
    assert run('import socket\nsocket.create_connection(("1.1.1.1", 80), timeout=1)')['result'] == 'unhandled_exception'
    assert run('while True: pass')['result'] == 'realtime_limited'
    assert run('import time\ntime.sleep(60)')['result'] == 'realtime_limited'
    assert run('import os\nwhile True: os.write(1, b"x"*65536)')['result'] == 'output_limited'
