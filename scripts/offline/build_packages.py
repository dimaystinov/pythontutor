"""Build deterministic, verified tar packages; upload to a draft GitHub release."""
import hashlib, json, os, tarfile, tempfile, urllib.request, urllib.error, http.client
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
lock = json.loads((ROOT / 'scripts/offline/assets.lock.json').read_text())
repo = os.environ.get('GITHUB_REPOSITORY', 'dimaystinov/pythontutor')
token = os.environ.get('GITHUB_TOKEN')
def api(path, data=None):
    req = urllib.request.Request('https://api.github.com/repos/' + repo + path,
        data=None if data is None else json.dumps(data).encode(),
        headers={'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json', 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=120) as response:
        return json.load(response)
release = None
if token:
    releases = api('/releases')
    release = next((r for r in releases if r['tag_name'] == lock['release']), None)
    if release is None:
        drafts = [r for r in releases if r['draft'] and r['name'] == 'PythonTutor 1.1 — автономный учебник и локальный ИИ']
        release = max(drafts, key=lambda r: len(r['assets']), default=None)
    if release and not release['draft']:
        raise SystemExit('Refusing to modify a published release')
    if not release:
        release = api('/releases', {'tag_name': lock['release'], 'target_commitish': os.environ['GITHUB_SHA'],
            'name': 'PythonTutor 1.1 — автономный учебник и локальный ИИ', 'draft': True,
            'body': 'Пакеты для локального помощника. Подготовка и проверка релиза продолжается.'})
def upload(path):
    if not release: return
    from urllib.parse import urlsplit, quote
    url = urlsplit(release['upload_url'].split('{')[0] + '?name=' + quote(path.name))
    connection = http.client.HTTPSConnection(url.hostname, timeout=600)
    with path.open('rb') as stream:
        connection.request('POST', url.path + '?' + url.query, body=stream,
            headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/octet-stream',
                'Content-Length': str(path.stat().st_size), 'User-Agent': 'PythonTutor-release'})
        response = connection.getresponse()
        if response.status != 201: raise RuntimeError(str(response.status) + response.read(2000).decode())
        response.read()
    connection.close()
files = {f['path']: f for f in lock['files']}
out = ROOT / 'dist/model-packages'
out.mkdir(parents=True, exist_ok=True)
for package in lock['packages']:
    if release and any(a['name'] == package['name'] for a in release['assets']):
        print('Already uploaded:', package['name'], flush=True)
        continue
    destination = out / package['name']
    with tarfile.open(destination, 'w', format=tarfile.USTAR_FORMAT) as archive:
        for name in package['files']:
            item = files[name]
            print('Downloading', name, flush=True)
            with tempfile.TemporaryFile() as stream:
                digest = hashlib.sha256(); size = 0
                with urllib.request.urlopen(item['source'], timeout=180) as response:
                    while chunk := response.read(1024 * 1024):
                        stream.write(chunk); digest.update(chunk); size += len(chunk)
                if size != item['size'] or digest.hexdigest() != item['sha256']:
                    raise RuntimeError('Integrity failure: ' + name)
                stream.seek(0)
                info = tarfile.TarInfo(name); info.size = size; info.mode = 0o644; info.mtime = 0
                archive.addfile(info, stream)
    upload(destination)
    print('Packaged:', destination.name, destination.stat().st_size, flush=True)
    if release: destination.unlink()
