#!/usr/bin/env python3
"""Stream one public Yandex model archive. No local copy, no arbitrary URL proxy."""
import json,re,threading,urllib.request,urllib.parse
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
API='https://cloud-api.yandex.net/v1/disk/public/resources/download?public_key='+urllib.parse.quote('https://disk.yandex.ru/d/OMU394wW8v-5KQ',safe='')
PATH='/model-download/qwen-yandex.zip'
SLOTS=threading.BoundedSemaphore(8)
class Handler(BaseHTTPRequestHandler):
 protocol_version='HTTP/1.1'
 def log_message(self,*args): pass # Never log signed upstream URLs.
 def send_common(self,status,length=None):
  self.send_response(status)
  self.send_header('Access-Control-Allow-Origin','*')
  self.send_header('Access-Control-Allow-Methods','GET, HEAD, OPTIONS')
  self.send_header('Access-Control-Allow-Headers','Range')
  self.send_header('Access-Control-Expose-Headers','Content-Length, Content-Range, Accept-Ranges')
  self.send_header('Cache-Control','no-store')
  self.send_header('X-Content-Type-Options','nosniff')
  if length is not None:self.send_header('Content-Length',str(length))
 def fail(self,status):
  data=b'Model download unavailable. Please use another source.'
  self.send_common(status,len(data));self.end_headers()
  if self.command!='HEAD':self.wfile.write(data)
 def do_OPTIONS(self):
  if self.path!=PATH:return self.fail(404)
  self.send_common(204,0);self.end_headers()
 def do_HEAD(self): self.do_GET()
 def do_GET(self):
  if self.path!=PATH:return self.fail(404)
  requested=self.headers.get('Range')
  if requested and not re.fullmatch(r'bytes=(?:\d+-\d*|-\d+)',requested):return self.fail(416)
  if not SLOTS.acquire(blocking=False):return self.fail(503)
  started=False
  try:
   with urllib.request.urlopen(API,timeout=30) as r:href=json.load(r)['href']
   u=urllib.parse.urlsplit(href)
   if u.scheme!='https' or not (u.hostname or '').endswith(('.yandex.ru','.yandex.net')):raise ValueError('Unexpected upstream')
   request=urllib.request.Request(href,headers={'Range':requested} if requested else {})
   with urllib.request.urlopen(request,timeout=30) as upstream:
    self.send_common(upstream.status,upstream.headers.get('Content-Length'))
    self.send_header('Content-Type','application/octet-stream')
    self.send_header('Accept-Ranges','bytes')
    if upstream.headers.get('Content-Range'):self.send_header('Content-Range',upstream.headers['Content-Range'])
    self.send_header('Connection','close');self.end_headers();started=True;self.close_connection=True
    if self.command!='HEAD':
     while True:
      chunk=upstream.read(256*1024)
      if not chunk:break
      self.wfile.write(chunk)
  except (BrokenPipeError,ConnectionResetError):pass
  except Exception:
   if not started:self.fail(502)
   else:self.close_connection=True
  finally:SLOTS.release()
if __name__=='__main__':ThreadingHTTPServer(('127.0.0.1',18766),Handler).serve_forever()
