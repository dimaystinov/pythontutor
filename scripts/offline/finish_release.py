"""Attach the verified application archives and checksums to the draft release."""
import importlib.util, json, os, urllib.request, hashlib, zipfile
from pathlib import Path
spec=importlib.util.spec_from_file_location('packages',Path(__file__).with_name('build_packages.py'))
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
root=p.ROOT
# Existing model assets are immutable inputs for this final packaging step.
release=p.api('/releases/'+str(p.release['id']))
expected={x['name'] for x in p.lock['packages']}
assert expected.issubset({x['name'] for x in release['assets']}), 'Missing model packages'
output=root/'dist/releases';output.mkdir(parents=True,exist_ok=True)
for folder,name in [(root, 'pythontutor-source-v1.1.0.zip'),(root/'dist/pages','pythontutor-pages-v1.1.0.zip')]:
    target=output/name
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as archive:
        if folder==root:
            import subprocess
            paths=[root/n for n in subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0') if n]
        else:paths=sorted(folder.rglob('*'))
        for path in paths:
            if path.is_file():archive.write(path,path.relative_to(folder))
    p.upload(target)
for path in [root/'tutorial/static/pwa/model-assets.json',root/'docs/licenses/QWEN-APACHE-2.0.txt',root/'docs/licenses/WHISPER-MIT.txt',root/'docs/licenses/MLC-APACHE-2.0.txt']:
    p.upload(path)
release=p.api('/releases/'+str(p.release['id']))
lines=[]
for asset in release['assets']:
    digest=asset.get('digest','')
    if digest.startswith('sha256:'):lines.append(digest[7:]+'  '+asset['name'])
assert len(lines)==len(release['assets']), 'GitHub did not return all SHA-256 digests'
sums=output/'SHA256SUMS.txt';sums.write_text('\n'.join(lines)+'\n');p.upload(sums)
body=(root/'docs/releases/v1.1.0.md').read_text()
req=urllib.request.Request('https://api.github.com/repos/'+p.repo+'/releases/'+str(release['id']),method='PATCH',data=json.dumps({'body':body,'target_commitish':os.environ['GITHUB_SHA']}).encode(),headers={'Authorization':'Bearer '+p.token,'Content-Type':'application/json'})
with urllib.request.urlopen(req) as response:assert response.status==200
print('Draft ready for final browser verification and publication.')
