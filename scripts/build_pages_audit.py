"""Browser acceptance harness: use exported tests and production Python worker."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
tasks=[]
for kind,folder in [('problem','solutions'),('image','images')]:
 for path in sorted((root/'knowledge'/folder).glob('*.json')):
  d=json.loads(path.read_text());tasks.append({'kind':kind,'slug':d['slug'],'code':d['recommended']['code']})
html='''<!doctype html><meta charset="utf-8"><meta name="execution-mode" content="browser"><title>Static course verification</title><script src="../static/js/browser-execution.js"></script><h1>Проверка всех задач статической версии</h1><button id="run">Проверить 142 задачи</button><pre id="result"></pre><script>
const tasks=TASKS;
document.querySelector('#run').onclick=async()=>{const out=document.querySelector('#result');document.querySelector('#run').disabled=true;out.textContent='';let checks=0,failures=0;for(const t of tasks){try{const response=await fetch('../browser/tests/'+t.kind+'/'+t.slug+'/index.json');if(!response.ok)throw Error('Missing exported tests');const {tests}=await response.json();const results=await BrowserPython.run({code:t.code,tests});checks+=results.length;const bad=results.filter(r=>r.result!=='ok');failures+=bad.length;out.textContent+=(bad.length?'FAIL ':'PASS ')+t.kind+'/'+t.slug+' '+results.length+' tests'+(bad.length?' '+JSON.stringify(bad).slice(0,700):'')+'\\n';}catch(e){failures++;out.textContent+='FAIL '+t.slug+' '+e.message+'\\n';}}out.textContent+='DONE '+tasks.length+' tasks, '+checks+' checks, '+failures+' failures';};</script>'''
p=root/'dist/pages/audit/index.html';p.parent.mkdir(exist_ok=True);p.write_text(html.replace('TASKS',json.dumps(tasks).replace('<','\\u003c')))
