"""Publish CI-built installers with the workflow's scoped GitHub token."""
import hashlib,json,os,urllib.request,urllib.error
from pathlib import Path
repo='dimaystinov/pythontutor';tag='desktop-v1.2.0';base='https://api.github.com/repos/'+repo
headers={'Authorization':'Bearer '+os.environ['GITHUB_TOKEN'],'Accept':'application/vnd.github+json','User-Agent':'PythonTutor-release'}
def request(url,body=None,content='application/json'):
 req=urllib.request.Request(url,data=body,headers={**headers,'Content-Type':content})
 with urllib.request.urlopen(req,timeout=120) as r:return json.load(r)
try:release=request(base+'/releases/tags/'+tag)
except urllib.error.HTTPError as e:
 if e.code!=404:raise
 release=request(base+'/releases',json.dumps({'tag_name':tag,'target_commitish':os.environ['GITHUB_SHA'],'name':'PythonTutor — установщик Windows и macOS','body':'Установщик скачивает учебник и OpenCode CLI, показывает прогресс и возобновляет загрузки. Опционально загружает все части Qwen 7B и Whisper. Автозапуск — в профиле пользователя. Для облачных моделей нужен интернет; доступность бесплатных моделей зависит от OpenCode. Приложения пока без цифровой подписи.','prerelease':True}).encode())
assets=list(Path('desktop-artifacts').rglob('*.exe'))+list(Path('desktop-artifacts').rglob('*.zip'))
checks=Path('desktop-artifacts/SHA256SUMS.txt');checks.write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in assets));assets.append(checks)
existing={a['name'] for a in release['assets']}
for p in assets:
 if p.name in existing:continue
 request(release['upload_url'].split('{')[0]+'?name='+p.name,p.read_bytes(),'application/octet-stream');print('Uploaded',p.name)
