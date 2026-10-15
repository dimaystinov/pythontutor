"""Loopback-only chat bridge. No generic proxy, file, shell or OpenCode control API."""
import functools, hmac, json, os, secrets, subprocess, tempfile, threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
PORT=8043
MODELS={'big-pickle','deepseek-v4.1-flash-free','mimo-v2.6-flash-free'}
ORIGINS={'https://dimaystinov.github.io',f'http://127.0.0.1:{PORT}',f'http://localhost:{PORT}'}
LOCK=threading.Lock()
def run_chat(binary, messages, model):
 if model not in MODELS:raise ValueError('Модель не входит в бесплатный список.')
 if not isinstance(messages,list) or not 1<=len(messages)<=15:raise ValueError('Неверный диалог.')
 for m in messages:
  if not isinstance(m,dict) or m.get('role') not in {'system','user','assistant'} or not isinstance(m.get('content'),str):raise ValueError('Неверное сообщение.')
 prompt='Отвечай только текстом. Не используй инструменты.\n'+json.dumps(messages,ensure_ascii=False)
 if len(prompt)>24000:raise ValueError('Слишком длинный диалог.')
 if not LOCK.acquire(blocking=False):raise ValueError('Дождитесь предыдущего ответа.')
 try:
  with tempfile.TemporaryDirectory(prefix='pythontutor-chat-') as work:
   env=os.environ.copy();env['XDG_CONFIG_HOME']=work
   # Keep CLI transcripts out of the next student's profile; reuse only provider auth.
   auth=Path(os.environ.get('XDG_DATA_HOME',Path.home()/'.local/share'))/'opencode/auth.json'
   env['XDG_DATA_HOME']=str(Path(work)/'data');env['XDG_CACHE_HOME']=str(Path(work)/'cache')
   if auth.exists():
    credentials=json.loads(auth.read_text());provider={k:v for k,v in credentials.items() if k=='opencode'}
    target=Path(env['XDG_DATA_HOME'])/'opencode/auth.json';target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(provider));target.chmod(0o600)
   env['OPENCODE_CONFIG_CONTENT']=json.dumps({'permission':{'*':'deny'},'share':'disabled','autoupdate':False,'agent':{'tutor':{'mode':'primary','description':'Text-only Python teacher','permission':{'*':'deny'},'prompt':'Ты преподаватель Python. Только текстовый ответ. Не используй инструменты.'}}})
   result=subprocess.run([str(binary),'run','--pure','--agent','tutor','--format','json','--model','opencode/'+model,prompt],cwd=work,env=env,capture_output=True,text=True,timeout=100,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
   parts=[];free_rejected=False
   for line in result.stdout.splitlines():
    try:event=json.loads(line)
    except ValueError:continue
    if event.get('type')=='error' and 'free tier' in str(event.get('error',{})).lower():free_rejected=True
    if event.get('type')=='text' and isinstance(event.get('part',{}).get('text'),str):parts.append(event['part']['text'])
   if free_rejected:raise ValueError('OpenCode ограничил использование бесплатного тарифа в этом режиме. Выберите локальный Qwen или настройте разрешённый доступ в OpenCode. Обход ограничений не выполняется.')
   if not parts:raise ValueError('OpenCode не вернул ответ. Проверьте интернет и доступ к бесплатной модели. В настройках OpenCode может потребоваться вход.')
   return '\n'.join(parts)[:10000]
 finally:LOCK.release()
def make_server(root,binary,token):
 site=root/'site'
 def current_binary():
  pointer=root/'cli-path'
  if pointer.exists():
   candidate=(root/pointer.read_text().strip()).resolve()
   if candidate.is_relative_to((root/'bin').resolve()):return candidate
  return binary
 class Handler(SimpleHTTPRequestHandler):
  def __init__(self,*a,**kw):super().__init__(*a,directory=str(site),**kw)
  def log_message(self,*a):pass
  def allowed(self):return self.headers.get('Origin') in ORIGINS
  def host_ok(self):return self.headers.get('Host') in {f'localhost:{PORT}',f'127.0.0.1:{PORT}'}
  def end_headers(self):
   if self.allowed():
    self.send_header('Access-Control-Allow-Origin',self.headers['Origin']);self.send_header('Vary','Origin');self.send_header('Access-Control-Allow-Private-Network','true')
   if self.path.startswith('/api/'):self.send_header('Cache-Control','no-store')
   super().end_headers()
  def respond(self,data,status=200):
   raw=json.dumps(data,ensure_ascii=False).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
  def do_OPTIONS(self):
   if not self.allowed() or not self.host_ok():self.respond({'error':'Origin rejected'},403);return
   self.send_response(204);self.send_header('Access-Control-Allow-Methods','POST, GET, OPTIONS');self.send_header('Access-Control-Allow-Headers','Content-Type, Authorization');self.end_headers()
  def do_GET(self):
   if not self.host_ok():self.respond({'error':'Host rejected'},403);return
   path=urlsplit(self.path).path
   if path=='/api/health':self.respond({'service':'pythontutor','cli':current_binary().exists()});return
   if path=='/api/pair':
    # Pairing secret is readable only by the locally served course, never CORS.
    if self.headers.get('Origin') not in {None,f'http://127.0.0.1:{PORT}',f'http://localhost:{PORT}'} or self.headers.get('Sec-Fetch-Site') not in {None,'same-origin','none'}:self.respond({'error':'Pair in desktop app'},403);return
    self.respond({'token':token});return
   if path.startswith('/api/'):self.respond({'error':'Not found'},404);return
   super().do_GET()
  def do_POST(self):
   if not self.host_ok() or not self.allowed() or not hmac.compare_digest(self.headers.get('Authorization',''),'Bearer '+token):self.respond({'error':'Подключите помощника в настройках.'},403);return
   if self.path!='/api/chat':self.respond({'error':'Not found'},404);return
   try:
    length=int(self.headers.get('Content-Length','0'))
    if not 0<length<=100000:raise ValueError('Неверный размер запроса.')
    data=json.loads(self.rfile.read(length));answer=run_chat(current_binary(),data.get('messages'),data.get('model'));self.respond({'answer':answer})
   except (ValueError,subprocess.TimeoutExpired) as e:self.respond({'error':str(e) if isinstance(e,ValueError) else 'OpenCode не ответил за 100 секунд.'},400)
   except (OSError,TypeError):self.respond({'error':'Не удалось запустить OpenCode. Откройте приложение PythonTutor и выполните обновление.'},503)
 return ThreadingHTTPServer(('127.0.0.1',PORT),Handler)
def serve(root,binary):
 tokenfile=root/'pairing-token';token=tokenfile.read_text().strip() if tokenfile.exists() else secrets.token_urlsafe(32)
 tokenfile.write_text(token);tokenfile.chmod(0o600)
 make_server(root,binary,token).serve_forever()
