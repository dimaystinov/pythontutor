"""Stage optional LocalSpeech 0.3.0 files for Pages, never in the app/course bundle.
Usage: python scripts/prepare_speech_assets.py /path/to/local-speech-checkout
Build SDK first with `node tools/build-sdk.cjs --runtime-only` in that checkout.
"""
import hashlib,json,shutil,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sdk=Path(sys.argv[1]);runtime=sdk/'dist/local-speech'
package=json.loads((runtime/'package-manifest.json').read_text())
assert package['version']=='0.3.0'
files=[];target=root/'dist/pages/static/local-speech/0.3.0'
for item in package['files']:
 if item['path']=='evidence/model-manifest.json':continue
 source=runtime/item['path'];data=source.read_bytes()
 assert len(data)==item['bytes'] and hashlib.sha256(data).hexdigest()==item['sha256']
 dest=target/item['path'];dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
 files.append({'path':item['path'],'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
models=[i for i in json.loads((sdk/'evidence/model-manifest.json').read_text()) if i['model'] in ('small','vad','context')]
for item in models:
 relative=f"models/{item['model']}/{item['file']}";data=(sdk/relative).read_bytes()
 assert len(data)==item['bytes'] and hashlib.sha256(data).hexdigest()==item['sha256']
 dest=target/relative;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
 files.append({'path':relative,'bytes':len(data),'sha256':item['sha256']})
relative='evidence/model-manifest.json';data=(json.dumps(models,ensure_ascii=False,indent=2)+'\n').encode()
(target/relative).parent.mkdir(parents=True,exist_ok=True);(target/relative).write_bytes(data);files.append({'path':relative,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
for model in ('small','vad','context'):
 source=sdk/'models'/model/'LICENSE'
 if source.exists():
  relative=f'models/{model}/LICENSE';data=source.read_bytes();(target/relative).write_bytes(data)
  files.append({'path':relative,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
manifest={'version':'0.3.0','source':'https://github.com/dimaystinov/local-speech/tree/8db716c','base':'https://dimaystinov.github.io/pythontutor/static/local-speech/0.3.0/','files':files}
(root/'tutorial/static/pwa/local-speech-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(len(files),'files,',sum(f['bytes'] for f in files),'bytes; optional assets:',target)
