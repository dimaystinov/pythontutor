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
 r=req(base+'/releases',json.dumps({'tag_name':tag,'target_commitish':os.environ['GITHUB_SHA'],'name':'PythonTutor '+version,'prerelease':False,'body':'PythonTutor 2.3.2. Настройки показывают установленные компоненты, скачивание с прогрессом и удаление. В списке помощников только установленные варианты. Переключение модели отменяет предыдущий ответ; выбор OpenCode сохраняется. Подсказки относятся к текущей задаче, обычная переписка сохраняется и видна при голосовом разговоре. OpenCode и голосовой ввод устанавливаются автоматически по запросу с прогрессом. Для запуска Qwen добавлено ограничение ожидания. Отказы бесплатного провайдера 403/429 показываются явно; доступность бесплатных моделей не гарантируется. Установщики без цифровой подписи.'}).encode())
files=list(Path('native-artifacts').rglob('*.exe'))+list(Path('native-artifacts').rglob('*.dmg'));assert len(files)==3,files
check=Path('native-artifacts/SHA256SUMS.txt');check.write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in files));files.append(check)
for p in files:
 if any(a['name']==p.name for a in r['assets']):continue
 from urllib.parse import quote
 req(r['upload_url'].split('{')[0]+'?name='+quote(p.name),p.read_bytes(),'application/octet-stream');print('Published',p.name)
