"""Create a manual browser audit of trusted course editorials; never submits progress."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
tasks=json.loads((root/'knowledge/problems.json').read_text())
for task in tasks:
    task['code']=json.loads((root/'knowledge/solutions'/(task['urlname']+'.json')).read_text())['recommended']['code']
payload=json.dumps([{'slug':t['urlname'],'code':t['code'],'tests':[{'stdin':i,'answer':a} for i,a in zip(t['tests'],t['answers'])]} for t in tasks],ensure_ascii=True).replace('<','\\u003c')
page='''<!doctype html><meta charset="utf-8"><meta name="execution-mode" content="browser"><title>Full browser course audit</title><script src="/static/js/browser-execution.js?v=5"></script><h1>Проверка 134 задач в браузере</h1><p>Эталонные программы, без записи ученического прогресса.</p><button id="run">Проверить весь курс</button><pre id="results"></pre><script>
const tasks=TASKS;document.querySelector('#run').onclick=async()=>{const out=document.querySelector('#results');document.querySelector('#run').disabled=true;out.textContent='';let checks=0,failed=0;for(const task of tasks){try{const r=await BrowserPython.run({code:task.code,tests:task.tests});const bad=r.filter(x=>x.result!=='ok');checks+=r.length;failed+=bad.length;out.textContent+=(bad.length?'FAIL ':'PASS ')+task.slug+' '+r.length+' tests'+(bad.length?' '+JSON.stringify(bad).slice(0,300):'')+'\\n';}catch(e){failed++;out.textContent+='FAIL '+task.slug+' '+e.message+'\\n';}}out.textContent+='DONE '+tasks.length+' tasks, '+checks+' tests, '+failed+' failures';document.querySelector('#run').disabled=false;};</script>'''
(root/'tutorial/static/tests/course-runtime.html').write_text(page.replace('TASKS',payload))
