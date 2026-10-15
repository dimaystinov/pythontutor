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

class AutostartTests(unittest.TestCase):
 def test_mac_registration_and_disable(self):
  import os,sys,plistlib
  with tempfile.TemporaryDirectory() as td:
   home=Path(td);root=home/'data';root.mkdir();exe=home/'download/PythonTutor.app/Contents/MacOS/PythonTutor';exe.parent.mkdir(parents=True);exe.write_bytes(b'test');exe.chmod(0o755)
   with patch.object(installer,'ROOT',root),patch.object(sys,'frozen',True,create=True),patch.object(sys,'platform','darwin'),patch.object(sys,'executable',str(exe)),patch('installer.Path.home',return_value=home):
    installer.install_autostart(True)
    plist=home/'Library/LaunchAgents/org.pythontutor.helper.plist'
    data=plistlib.loads(plist.read_bytes());self.assertTrue(data['RunAtLoad']);self.assertEqual(data['ProgramArguments'][-1],'--serve');self.assertTrue(Path(data['ProgramArguments'][0]).exists())
    installer.install_autostart(False);self.assertFalse(plist.exists())
 def test_windows_registration_and_disable(self):
  import sys,types
  from unittest.mock import MagicMock
  with tempfile.TemporaryDirectory() as td:
   root=Path(td)/'data';root.mkdir();exe=Path(td)/'setup.exe';exe.write_bytes(b'test')
   registry=types.SimpleNamespace(HKEY_CURRENT_USER=1,REG_SZ=1,CreateKey=MagicMock(),SetValueEx=MagicMock(),DeleteValue=MagicMock())
   with patch.object(installer,'ROOT',root),patch.object(sys,'frozen',True,create=True),patch.object(sys,'platform','win32'),patch.object(sys,'executable',str(exe)),patch.dict(sys.modules,{'winreg':registry}),patch.dict(installer.os.environ,{'APPDATA':str(Path(td)/'roaming')}),patch('installer.subprocess.run'):
    installer.install_autostart(True);self.assertIn('--serve',registry.SetValueEx.call_args.args[-1]);self.assertEqual(len(list((root/'launchers').rglob('*.exe'))),1)
    installer.install_autostart(False);registry.DeleteValue.assert_called_once()

class CompleteInstallTests(unittest.TestCase):
 def test_all_offline_parts_installed_without_user_selection(self):
  import tarfile
  with tempfile.TemporaryDirectory() as td:
   p=Path(td);root=p/'install';fixtures=p/'fixtures';fixtures.mkdir();manifest={'release':'vtest','files':[],'packages':[]}
   for group in ['qwen7b','whisper-tiny']:
    data=(group+' content').encode();name=group+'/data.bin';pack=group+'.tar'
    manifest['files'].append({'path':name,'group':group,'size':len(data),'sha256':hashlib.sha256(data).hexdigest()})
    manifest['packages'].append({'name':pack,'group':group,'files':[name]})
    with tarfile.open(fixtures/pack,'w') as tar:
     info=tarfile.TarInfo(name);info.size=len(data);tar.addfile(info,io.BytesIO(data))
   with zipfile.ZipFile(fixtures/'course.zip','w') as z:
    z.writestr('repo/index.html','course');z.writestr('repo/static/pwa/model-assets.json',json.dumps(manifest))
   with zipfile.ZipFile(fixtures/'cli.zip','w') as z:z.writestr('opencode','cli')
   release={'tag_name':'vtest','assets':[{'name':'opencode-darwin-arm64.zip','digest':'sha256:'+hashlib.sha256((fixtures/'cli.zip').read_bytes()).hexdigest(),'browser_download_url':'https://github.com/cli.zip'}]}
   downloads=[];progress=[]
   def fake_download(url,target,callback,expected=None):
    downloads.append(url);target.parent.mkdir(parents=True,exist_ok=True)
    src=fixtures/('course.zip' if '/zipball/' in url else url.rsplit('/',1)[1]);target.write_bytes(src.read_bytes());callback(target.stat().st_size,0);return target
   with patch.object(installer,'ROOT',root),patch.object(installer,'BINARY',root/'bin/opencode'),patch.object(installer.sys,'platform','darwin'),patch('installer.platform.machine',return_value='arm64'),patch('installer.api',side_effect=[{'commit':{'sha':'test'}},release]),patch('installer.download',side_effect=fake_download):
    installer.install(lambda _,v:progress.append(v),True)
   self.assertEqual(len(downloads),4);self.assertTrue(all(0<=x<=100 for x in progress));self.assertEqual(progress[-1],100)
   for group in ['qwen7b','whisper-tiny']:self.assertEqual((root/'site/pythontutor/static/models'/group/'data.bin').read_text(),group+' content')
   self.assertTrue((root/'site/pythontutor/static/models/installed.json').exists());self.assertTrue((root/(root/'cli-path').read_text()).exists())
