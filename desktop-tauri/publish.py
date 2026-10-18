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
 r=req(base+'/releases',json.dumps({'tag_name':tag,'target_commitish':os.environ['GITHUB_SHA'],'name':'PythonTutor '+version,'prerelease':False,'body':'PythonTutor 2.1.2. Условия задач стали крупнее и контрастнее. В приложении убран лишний блок скачивания уже установленного курса. Исправлена установка компонентов: Qwen 7B и голосовой ввод скачиваются по одной кнопке, без выбора файлов и переходов на старые релизы. Прогресс, отмена и повторная попытка доступны в настройках. Обновления из настроек: установленная и актуальная версия, скачивание проверенного установщика с прогрессом. Консультант работает сразу без скачивания нейросетей. Прогресс загрузки LocalSpeech, моделей и курса. Встроенный консультант: объяснения ошибок Python, разбор отдельных тестов, подсказки и ссылки на теорию. LocalSpeech 0.3.0 с русским голосовым вводом скачивается отдельно (около 43 МБ). В настройках можно удалить скачанные компоненты, сохранив курс и данные ученика. OpenCode и Qwen остаются дополнительными режимами. Для OpenCode нужен интернет. В Windows используется системный WebView2. Если его нет, небольшой встроенный загрузчик установит его из интернета с отображением прогресса. Установщики пока без цифровой подписи.'}).encode())
files=list(Path('native-artifacts').rglob('*.exe'))+list(Path('native-artifacts').rglob('*.dmg'));assert len(files)==3,files
check=Path('native-artifacts/SHA256SUMS.txt');check.write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in files));files.append(check)
for p in files:
 if any(a['name']==p.name for a in r['assets']):continue
 from urllib.parse import quote
 req(r['upload_url'].split('{')[0]+'?name='+quote(p.name),p.read_bytes(),'application/octet-stream');print('Published',p.name)
