import importlib.util,io,json,threading,unittest,http.client
from unittest.mock import patch
from pathlib import Path
spec=importlib.util.spec_from_file_location('proxy',Path(__file__).with_name('proxy.py'));proxy=importlib.util.module_from_spec(spec);spec.loader.exec_module(proxy)
class Upstream(io.BytesIO):
 status=206
 headers={'Content-Length':'3','Content-Range':'bytes 0-2/4296797134'}
class TestProxy(unittest.TestCase):
 def test_stream_and_cors(self):
  def open_(url,**kw):
   if isinstance(url,str):return io.BytesIO(json.dumps({'href':'https://downloader.disk.yandex.ru/public-test'}).encode())
   self.assertEqual(url.headers['Range'],'bytes=0-2');return Upstream(b'abc')
  server=proxy.ThreadingHTTPServer(('127.0.0.1',0),proxy.Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  try:
   with patch.object(proxy.urllib.request,'urlopen',open_):
    c=http.client.HTTPConnection(*server.server_address);c.request('GET',proxy.PATH,headers={'Range':'bytes=0-2'});r=c.getresponse();self.assertEqual(r.status,206);self.assertEqual(r.getheader('Access-Control-Allow-Origin'),'*');self.assertEqual(r.read(),b'abc');c.close()
   c=http.client.HTTPConnection(*server.server_address);c.request('GET','/?url=http://internal');r=c.getresponse();self.assertEqual(r.status,404);r.read();c.close()
   c=http.client.HTTPConnection(*server.server_address);c.request('OPTIONS',proxy.PATH);r=c.getresponse();self.assertEqual(r.status,204);self.assertEqual(r.getheader('Access-Control-Allow-Headers'),'Range');c.close()
  finally:server.shutdown();server.server_close()
if __name__=='__main__':unittest.main()
