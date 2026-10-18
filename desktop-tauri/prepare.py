"""Prepare the offline course. Optional OpenCode is downloaded only on user request."""
import base64,hashlib,json,os,platform,shutil,subprocess,sys,urllib.request,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];HERE=Path(__file__).resolve().parent
out=HERE/'frontend';out.mkdir(exist_ok=True)
python=ROOT/'.venv314/bin/python'
if not python.exists():python=Path(sys.executable)
subprocess.run([str(python),str(ROOT/'scripts/build_pages.py'),'--output','desktop-tauri/frontend/pythontutor'],cwd=ROOT,check=True)
for p in (HERE/'ui').iterdir():shutil.copy2(p,out/p.name)
for p in (out/'pythontutor').rglob('*.html'):
 s=p.read_text();s=s.replace('<meta name="learner-id" content="local">','<meta name="learner-id" content="local"><script src="/native.js"></script><script src="/update-settings.js"></script>');p.write_text(s)
# Native SQLite replaces browser-only progress, without changing the browser site.
p=out/'pythontutor/static/pwa/storage.js';s=p.read_text();s=s.replace("async function get(kind,slug){return", "async function get(kind,slug){if(window.TutorNative)return (await list()).find(r=>r.kind===kind&&r.slug===slug);return")
s=s.replace("await query('readwrite',s=>{requireCurrent();return s.put(item);});", "if(window.TutorNative)await TutorNative.invoke('save_solution',{data:item});else await query('readwrite',s=>{requireCurrent();return s.put(item);});")
s=s.replace("async function list(){return", "async function list(){if(window.TutorNative)return TutorNative.invoke('solutions');return")
s=s.replace(" const d=await db();\n await new Promise", " if(window.TutorNative)await TutorNative.invoke('reset_progress');\n const d=await db();\n await new Promise")
p.write_text(s)
p=out/'pythontutor/static/pwa/local-ai.js';s=p.read_text().replace("if(id==='opencode-local'){", "if(id==='opencode-local'){\n  if(window.TutorNative)return null;",1)
s=s.replace(" await load('opencode-local');", " if(window.TutorNative){await window.TutorNative.ensureCLI();progress?.('Питоныч отвечает…');const answer=await TutorNative.invoke('chat',{model:document.getElementById('tutor-api-model').value,messages:dialogueMessages('opencode-local',payload)});return hintOnly(answer,payload.solved);}\n await load('opencode-local');")
s=s.replace("function stop(){", "function stop(){if(window.TutorNative)TutorNative.invoke('cancel_chat');")
p.write_text(s)
p=out/'pythontutor/static/js/assistant.js';s=p.read_text().replace("location.origin==='http://127.0.0.1:8043'", "(window.TutorNative||location.origin==='http://127.0.0.1:8043')")
# Keep the user's choice between local inference and OpenCode.
p.write_text(s)
p=out/'pythontutor/static/pwa/app.js';s=p.read_text().replace("if('serviceWorker' in navigator)","if(window.TutorNative){say('Курс установлен на этом компьютере.');}else if('serviceWorker' in navigator)");s=s.replace('if(backupKey(key))data[key]',"if(backupKey(key)&&(!/^(problem-draft:|image-draft:|tutor-local-chat:)/.test(key)||key.split(':')[1]===TutorDevice.owner()))data[key]")
s=s.replace('localStorage.setItem(key,value);await progress()',"localStorage.setItem(key.replace(/^(problem-draft:|image-draft:|tutor-local-chat:)[^:]+:/,(_,p)=>p+TutorDevice.owner()+':'),value);await progress()")
p.write_text(s)
print('Course, Python runtime, tests and photos prepared. OpenCode is installed on request.')
