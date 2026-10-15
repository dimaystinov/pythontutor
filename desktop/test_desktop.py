import hashlib,io,json,tempfile,threading,unittest,urllib.request,urllib.error,zipfile
from pathlib import Path
from unittest.mock import patch
import bridge,installer
class DesktopTests(unittest.TestCase):
 def test_zip_traversal(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td);z=p/'bad.zip'
   with zipfile.ZipFile(z,'w') as f:f.writestr('../escape','bad')
   with self.assertRaises(ValueError):installer.unzip(z,p/'out')
   self.assertFalse((p/'escape').exists())
 def test_cli_no_tools_and_model_allowlist(self):
  result=type('Result',(),{'stdout':json.dumps({'type':'text','part':{'text':'Ответ'}})})()
  with patch('bridge.subprocess.run',return_value=result) as run:
   self.assertEqual(bridge.run_chat(Path('opencode'),[{'role':'user','content':'input()'}],'big-pickle'),'Ответ')
   args,kwargs=run.call_args;self.assertIn('--pure',args[0]);self.assertEqual(json.loads(kwargs['env']['OPENCODE_CONFIG_CONTENT'])['permission'],{'*':'deny'})
   self.assertFalse(kwargs.get('shell',False))
  with self.assertRaises(ValueError):bridge.run_chat(Path('opencode'),[],'paid')
 def test_bridge_rejects_other_origins_and_no_token(self):
  with tempfile.TemporaryDirectory() as td:
   server=bridge.make_server(Path(td),Path('opencode'),'test-token');threading.Thread(target=server.serve_forever,daemon=True).start()
   try:
    for origin,auth in [('https://evil.invalid','Bearer test-token'),('https://dimaystinov.github.io','')]:
     r=urllib.request.Request('http://127.0.0.1:8043/api/chat',data=b'{}',headers={'Origin':origin,'Authorization':auth,'Content-Type':'application/json'})
     with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(r)
     self.assertEqual(error.exception.code,403)
    r=urllib.request.Request('http://127.0.0.1:8043/api/pair',headers={'Origin':'https://dimaystinov.github.io'})
    with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen(r)
   finally:server.shutdown();server.server_close()
 def test_download_resumes_and_checks_digest(self):
  class Response(io.BytesIO):
   status=206
   headers={'Content-Length':'3'}
  with tempfile.TemporaryDirectory() as td:
   target=Path(td)/'asset.zip';target.with_suffix('.zip.partial').write_bytes(b'abc')
   with patch('installer.urllib.request.urlopen',return_value=Response(b'def')) as network:
    installer.download('https://github.com/test',target,lambda *_:None,hashlib.sha256(b'abcdef').hexdigest())
    self.assertEqual(network.call_args.args[0].get_header('Range'),'bytes=3-');self.assertEqual(target.read_bytes(),b'abcdef')
if __name__=='__main__':unittest.main()
