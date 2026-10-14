"""Full built-image regression: catches a missing/incompatible Docker client."""
import os
import secrets
import subprocess
import uuid

import pytest


@pytest.mark.skipif(os.getenv('RUN_CONTROL_PLANE_TESTS') != '1', reason='Requires built runner/worker images and Docker socket')
def test_built_controlplane_http_to_worker():
    image = 'pythontutor-runner:local'
    version = subprocess.run(['docker', 'run', '--rm', '--entrypoint', 'docker', image, '--version'],
                             capture_output=True, text=True, check=True, timeout=30)
    assert 'Docker version' in version.stdout
    name = 'pythontutor-control-test-' + uuid.uuid4().hex
    environment = dict(os.environ, RUNNER_TOKEN=secrets.token_hex(32))
    client = '''import json, os, time, urllib.request
for attempt in range(40):
    try:
        urllib.request.urlopen('http://127.0.0.1:8081/healthz', timeout=1)
        break
    except OSError:
        time.sleep(0.1)
request = urllib.request.Request('http://127.0.0.1:8081/execute',
    data=json.dumps({'code':'import sys; print(sys.version.split()[0]); print(42)', 'stdin':'', 'explain':False}).encode(),
    headers={'Authorization':'Bearer '+os.environ['RUNNER_TOKEN'], 'Content-Type':'application/json'})
result=json.load(urllib.request.urlopen(request, timeout=20))
assert result['result']=='ok', result
assert result['stdout']=='3.14.7\\n42\\n', result
print('Authenticated control-plane -> Docker socket -> Python 3.14.7 worker: PASS')
'''
    try:
        subprocess.run(['docker','run','-d','--name',name,'--network=none','--read-only',
                        '--cap-drop=ALL','--security-opt=no-new-privileges',
                        '--tmpfs','/tmp:rw,noexec,nosuid,size=32m',
                        '-v','/var/run/docker.sock:/var/run/docker.sock','-e','RUNNER_TOKEN',image],
                       env=environment, capture_output=True, check=True, timeout=30)
        response = subprocess.run(['docker','exec',name,'python','-c',client],
                                  capture_output=True,text=True,timeout=30)
        assert response.returncode == 0, response.stdout + response.stderr
    finally:
        subprocess.run(['docker','rm','-f',name],capture_output=True,timeout=10)
