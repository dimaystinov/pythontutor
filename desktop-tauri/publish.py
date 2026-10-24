import hashlib,json,os,urllib.request,urllib.error
from pathlib import Path
base='https://api.github.com/repos/dimaystinov/pythontutor'
version=json.loads((Path(__file__).parent/'package.json').read_text())['version']
tag='app-v'+version
headers={'Authorization':'Bearer '+os.environ['GITHUB_TOKEN'],'Accept':'application/vnd.github+json','User-Agent':'PythonTutor-release'}
def req(url,data=None,content='application/json'):
 with urllib.request.urlopen(urllib.request.Request(url,data=data,headers={**headers,'Content-Type':content}),timeout=300) as r:return json.load(r)
try:r=req(base+'/releases/tags/'+tag)
except urllib.error.HTTPError as e:
 if e.code!=404:raise
 r=req(base+'/releases',json.dumps({'tag_name':tag,'target_commitish':os.environ['GITHUB_SHA'],'name':'PythonTutor '+version,'prerelease':False,'body':'PythonTutor 2.3.3. Исправлена изоляция черновиков локальных аккаунтов. Очистка удаляет прогресс, код и переписку текущего ученика; другие профили и скачанные компоненты сохраняются. Устранены устаревшие отметки решённых задач. Установщики для Windows x64 и macOS Apple Silicon, без цифровой подписи.'}).encode())
files=list(Path('native-artifacts').rglob('*.exe'))+list(Path('native-artifacts').rglob('*.dmg'));assert len(files)==2 and {p.name for p in files}=={f"PythonTutor_{version}_x64-setup.exe",f"PythonTutor_{version}_aarch64.dmg"},files
check=Path('native-artifacts/SHA256SUMS.txt');check.write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in files));files.append(check)
for p in files:
 if any(a['name']==p.name for a in r['assets']):continue
 from urllib.parse import quote
 req(r['upload_url'].split('{')[0]+'?name='+quote(p.name),p.read_bytes(),'application/octet-stream');print('Published',p.name)
