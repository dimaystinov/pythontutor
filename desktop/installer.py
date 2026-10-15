"""Frozen Windows/macOS installer and per-user background launcher."""
import hashlib,json,os,platform,plistlib,queue,shutil,subprocess,sys,tarfile,threading,time,urllib.request,webbrowser,zipfile
from pathlib import Path
from bridge import serve,PORT,LOCK
ROOT=Path(os.environ.get('LOCALAPPDATA',Path.home()/'Library/Application Support'))/'PythonTutor'
BINARY=ROOT/'bin'/('opencode.exe' if sys.platform=='win32' else 'opencode')
UA={'User-Agent':'PythonTutor-Installer/1.2'}
def api(url):
 with urllib.request.urlopen(urllib.request.Request(url,headers=UA),timeout=30) as r:return json.load(r)
def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def download(url,target,progress,expected=None):
 target.parent.mkdir(parents=True,exist_ok=True)
 if target.exists() and (not expected or digest(target)==expected):return target
 partial=target.with_suffix(target.suffix+'.partial')
 for attempt in range(3):
  offset=partial.stat().st_size if partial.exists() else 0
  headers={**UA,**({'Range':f'bytes={offset}-'} if offset else {})}
  try:
   with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=45) as r:
    if r.status!=206:offset=0
    total=offset+int(r.headers.get('Content-Length',0));done=offset
    with partial.open('ab' if offset else 'wb') as f:
     while chunk:=r.read(1024*1024):
      f.write(chunk);done+=len(chunk);progress(done,total)
   if total and done!=total:raise OSError('Загрузка оборвалась.')
   if expected and digest(partial)!=expected:
    partial.unlink();raise OSError('Контрольная сумма не совпала. Повторяю загрузку.')
   partial.replace(target);return target
  except OSError:
   if attempt==2:raise
   time.sleep(attempt+1)
def safe_path(base,name):
 target=(base/name).resolve()
 if not target.is_relative_to(base.resolve()):raise ValueError('Небезопасный путь в архиве.')
 return target
def unzip(archive,dest):
 with zipfile.ZipFile(archive) as z:
  for item in z.infolist():
   target=safe_path(dest,item.filename)
   if (item.external_attr>>16)&0o170000==0o120000:raise ValueError('Символические ссылки в архиве запрещены.')
   if item.is_dir():target.mkdir(parents=True,exist_ok=True);continue
   target.parent.mkdir(parents=True,exist_ok=True)
   with z.open(item) as src,target.open('wb') as dst:shutil.copyfileobj(src,dst)
def install(progress,offline=False):
 ROOT.mkdir(parents=True,exist_ok=True);cache=ROOT/'downloads'
 progress('Получаю список файлов',0)
 branch=api('https://api.github.com/repos/dimaystinov/pythontutor/branches/gh-pages');sha=branch['commit']['sha']
 release=api('https://api.github.com/repos/anomalyco/opencode/releases/latest')
 machine=platform.machine().lower();arch='arm64' if machine in {'arm64','aarch64'} else 'x64'
 assetname=('opencode-windows-x64-baseline.zip' if sys.platform=='win32' else f'opencode-darwin-{arch}'+('-baseline' if arch=='x64' else '')+'.zip')
 asset=next(a for a in release['assets'] if a['name']==assetname)
 expected=asset.get('digest','').removeprefix('sha256:')
 if len(expected)!=64:raise ValueError('GitHub не предоставил контрольную сумму OpenCode. Установка остановлена.')
 jobs=[('Учебник',f'https://api.github.com/repos/dimaystinov/pythontutor/zipball/{sha}',cache/(sha+'.zip'),None),('OpenCode CLI',asset['browser_download_url'],cache/(release['tag_name']+'-'+assetname),expected)]
 for i,(label,url,target,sha256) in enumerate(jobs):download(url,target,lambda d,t:progress(label+(f' · {d//1048576} МБ' if not t else ''), (i+(d/t if t else 0))*60/len(jobs)),sha256)
 progress('Распаковываю учебник',62);staging=ROOT/'site-new';shutil.rmtree(staging,ignore_errors=True);unzip(jobs[0][2],staging)
 source=next(p for p in staging.iterdir() if p.is_dir())
 if not (source/'index.html').is_file() or not (source/'static/pwa/model-assets.json').is_file():raise ValueError('В архиве отсутствует учебник.')
 site=ROOT/'site'/'pythontutor';site.mkdir(parents=True,exist_ok=True);shutil.copytree(source,site,dirs_exist_ok=True);shutil.rmtree(staging)
 progress('Настраиваю OpenCode CLI',67);bin_stage=ROOT/'bin-new';shutil.rmtree(bin_stage,ignore_errors=True);unzip(jobs[1][2],bin_stage)
 exe=next(bin_stage.rglob('opencode.exe' if sys.platform=='win32' else 'opencode'));BINARY.parent.mkdir(exist_ok=True)
 versioned=ROOT/'bin'/release['tag_name']/BINARY.name;versioned.parent.mkdir(parents=True,exist_ok=True)
 if not versioned.exists():shutil.copy2(exe,versioned);versioned.chmod(0o755)
 (ROOT/'cli-path').write_text(str(versioned.relative_to(ROOT)))
 shutil.rmtree(bin_stage)
 if offline:
  (site/'static/models/installed.json').unlink(missing_ok=True)
  manifest=json.loads((site/'static/pwa/model-assets.json').read_text());files={x['path']:x for x in manifest['files']};packs=manifest['packages'];
  for i,pack in enumerate(packs):
   url='https://github.com/dimaystinov/pythontutor/releases/download/'+manifest['release']+'/'+pack['name'];archive=cache/pack['name']
   download(url,archive,lambda d,t:progress('ИИ: '+pack['name'],70+(i+(d/t if t else 0))*27/len(packs)))
   seen=set()
   with tarfile.open(archive) as tar:
    for member in tar:
     if member.name in seen:raise ValueError('Повторный файл в пакете ИИ.')
     seen.add(member.name);item=files.get(member.name)
     if not member.isfile() or not item or member.size!=item['size']:raise ValueError('Неизвестный файл в пакете ИИ.')
     target=safe_path(site/'static/models',member.name.replace('ndarray-cache.json','tensor-cache.json'));target.parent.mkdir(parents=True,exist_ok=True)
     with tar.extractfile(member) as src,target.open('wb') as dst:shutil.copyfileobj(src,dst)
     if digest(target)!=item['sha256']:target.unlink();raise ValueError('Повреждён файл ИИ. Повторите установку.')
   if seen!=set(pack['files']):raise ValueError('Пакет ИИ неполный. Повторите установку.')
  (site/'static/models/installed.json').write_text(json.dumps({'groups':['qwen7b','whisper-tiny']}))
 (ROOT/'installed.json').write_text(json.dumps({'course':sha,'opencode':release['tag_name']}));progress('Готово',100)
def install_autostart(enabled):
 if not getattr(sys,'frozen',False):return # Source checkout never registers itself.
 exe=Path(sys.executable)
 if sys.platform=='win32':
  import winreg
  app=ROOT/'launchers'/digest(exe)[:12]/'PythonTutor.exe';app.parent.mkdir(parents=True,exist_ok=True)
  if exe.resolve()!=app.resolve():shutil.copy2(exe,app)
  with winreg.CreateKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\Run') as key:
   if enabled:winreg.SetValueEx(key,'PythonTutor',0,winreg.REG_SZ,f'"{app}" --serve')
   else:
    try:winreg.DeleteValue(key,'PythonTutor')
    except FileNotFoundError:pass
  menu=Path(os.environ['APPDATA'])/'Microsoft/Windows/Start Menu/Programs/PythonTutor';menu.mkdir(parents=True,exist_ok=True)
  env=os.environ.copy();env['TUTOR_EXE']=str(app);env['TUTOR_LINK']=str(menu/'PythonTutor.lnk')
  subprocess.run(['powershell','-NoProfile','-Command',"$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:TUTOR_LINK);$s.TargetPath=$env:TUTOR_EXE;$s.Save()"],env=env,check=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
 else:
  original=exe.parents[2];app=Path.home()/'Applications'/'PythonTutor.app';app.parent.mkdir(exist_ok=True)
  if original!=app:shutil.copytree(original,app,dirs_exist_ok=True)
  plist=Path.home()/'Library/LaunchAgents/org.pythontutor.helper.plist';plist.parent.mkdir(parents=True,exist_ok=True)
  if enabled:
   with plist.open('wb') as f:plistlib.dump({'Label':'org.pythontutor.helper','ProgramArguments':[str(app/'Contents/MacOS/PythonTutor'),'--serve'],'RunAtLoad':True,'KeepAlive':False},f)
  else:plist.unlink(missing_ok=True)
 (ROOT/'preferences.json').write_text(json.dumps({'autostart':enabled}))
def start_service():
 try:
  if api(f'http://127.0.0.1:{PORT}/api/health').get('service')=='pythontutor':return
 except OSError:pass
 if getattr(sys,'frozen',False):subprocess.Popen([sys.executable,'--serve'],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),start_new_session=sys.platform!='win32')
 else:threading.Thread(target=serve,args=(ROOT,BINARY),daemon=True).start()
 for _ in range(30):
  try:
   if api(f'http://127.0.0.1:{PORT}/api/health').get('service')=='pythontutor':return
  except OSError:time.sleep(.1)
 raise RuntimeError('Не удалось запустить помощника на порту 8043. Закройте другую программу, использующую этот порт.')
def main():
 ROOT.mkdir(parents=True,exist_ok=True)
 if '--self-test' in sys.argv:
  import tkinter
  tkinter.Tcl().eval('info patchlevel');return
 if '--serve' in sys.argv:serve(ROOT,BINARY);return
 import tkinter as tk
 from tkinter import ttk
 window=tk.Tk();window.title('PythonTutor');window.geometry('680x450');events=queue.Queue()
 ttk.Label(window,text='PythonTutor — установка и обновление',font=('',18)).pack(pady=16)
 ttk.Label(window,text='Учебник и OpenCode CLI будут установлены автоматически.\nOpenCode использует интернет; локальный Qwen работает офлайн.').pack()
 offline=tk.BooleanVar(value=False);autostart=tk.BooleanVar(value=json.loads((ROOT/'preferences.json').read_text()).get('autostart',True) if (ROOT/'preferences.json').exists() else True)
 ttk.Checkbutton(window,text='Добавить Qwen 7B и голосовой ввод для работы офлайн (4,4 ГБ)',variable=offline).pack(pady=8)
 ttk.Checkbutton(window,text='Запускать помощника при входе в систему',variable=autostart).pack()
 bar=ttk.Progressbar(window,maximum=100,length=550);bar.pack(pady=12);status=ttk.Label(window,text='Готов к установке',wraplength=620);status.pack()
 def work(with_offline,auto):
  try:install(lambda text,value:events.put((text,value)),with_offline);install_autostart(auto);start_service();events.put(('done',100))
  except Exception as e:events.put(('Ошибка: '+str(e),-1))
 def begin():button.config(state='disabled');threading.Thread(target=work,args=(offline.get(),autostart.get()),daemon=True).start()
 button=ttk.Button(window,text='Установить / обновить',command=begin);button.pack(pady=8)
 def open_course():start_service();webbrowser.open(f'http://127.0.0.1:{PORT}/pythontutor/')
 ttk.Button(window,text='Открыть учебник',command=open_course).pack()
 ttk.Label(window,text='Код для подключения помощника на сайте GitHub:').pack(pady=(12,0))
 pairing=tk.StringVar(value='Появится после запуска учебника')
 entry=ttk.Entry(window,textvariable=pairing,width=62,state='readonly');entry.pack()
 def copy_code():
  token=ROOT/'pairing-token'
  if token.exists():window.clipboard_clear();window.clipboard_append(token.read_text().strip())
 ttk.Button(window,text='Скопировать код подключения',command=copy_code).pack()

 def poll():
  token=ROOT/'pairing-token'
  if token.exists():pairing.set(token.read_text().strip())
  while not events.empty():
   text,value=events.get()
   if text=='done':text='Установлено. Можно открыть учебник.';button.config(state='normal');open_course()
   if value<0:button.config(state='normal')
   else:bar['value']=value
   status.config(text=text)
  window.after(150,poll)
 poll();window.mainloop()
if __name__=='__main__':main()
