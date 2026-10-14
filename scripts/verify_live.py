#!/usr/bin/env python3
"""Integration check against a running deployment (records test submissions).

Supply a test account using TUTOR_USERNAME / TUTOR_PASSWORD. This checks actual
HTTP + CSRF + database + control-plane + worker execution, not mocked results.
"""
import argparse
import base64
import io
import json
import os
from pathlib import Path
import requests
from PIL import Image

parser = argparse.ArgumentParser()
parser.add_argument('--url', default='http://localhost:8042')
parser.add_argument('--credentials', type=Path, help='Local JSON with username/password, never sent as a file')
args = parser.parse_args()
credentials = json.loads(args.credentials.read_text()) if args.credentials else {'username': os.environ['TUTOR_USERNAME'], 'password': os.environ['TUTOR_PASSWORD']}
root = Path(__file__).resolve().parents[1]
session = requests.Session()
session.trust_env = False


def get(path):
    response = session.get(args.url + path, timeout=20)
    response.raise_for_status()
    return response


def post(path, data):
    response = session.post(args.url + path, data=data,
        headers={'X-CSRFToken': session.cookies['csrftoken'], 'Referer': args.url + path}, timeout=150)
    response.raise_for_status()
    return response


assert get('/healthz/').json()['status'] == 'ok'
get('/accounts/login/')
response = post('/accounts/login/', {k: credentials[k] for k in ('username', 'password')})
assert '/accounts/login/' not in response.url, 'Login rejected'
get('/visualizer/')
result = post('/visualizer/execute/', {'user_script': 'def fact(n):\n    return 1 if n == 0 else n * fact(n-1)\nprint(fact(5))', 'input_data': '', 'explain': 'true'}).json()
assert result['result'] == 'ok', result
assert result['trace'][-1]['stdout'].strip() == '120', result
print('PASS recursive step trace over HTTP', flush=True)
for code, expected in [('print(sum(int(input()) for _ in range(3)))', 'ok'), ('print(0)', 'error')]:
    result = post('/tester/submit/', {'problem': 'aplusbplusc', 'user_code': code}).json()
    assert result['status'] == expected, result
print('PASS accepted and rejected traditional submissions', flush=True)
catalog = json.loads((root / 'image_course/catalog.json').read_text())
for task in catalog:
    result = post(f'/images/{task["slug"]}/submit/', {'code': task['solution']}).json()
    assert result['status'] == 'ok' and result['tests'] == ['ok'] * len(task['tests']), (task['slug'], result)
    print(f'PASS {task["slug"]}: {len(result["tests"])} images', flush=True)
task = catalog[0]
result = post(f'/images/{task["slug"]}/run/', {'code': task['solution']}).json()
assert result['result'] == 'ok' and result['image']
with Image.open(io.BytesIO(base64.b64decode(result['image'], validate=True))) as image:
    assert image.format == 'PNG' and image.size == (256, 192)
bad = post(f'/images/{task["slug"]}/submit/', {'code': "print('No image')"}).json()
assert bad['status'] == 'error'
print('PASS image preview and missing-output rejection', flush=True)
print('All live integration checks passed.', flush=True)
