"""Browser regression harness: correct masks accepted; blank masks rejected."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
tasks=[t for t in json.loads((root/'image_course/catalog.json').read_text()) if t['slug'].startswith('hsv-')]
html='''<!doctype html><meta charset="utf-8"><meta name="execution-mode" content="browser"><title>HSV browser regression</title><script src="../static/js/browser-execution.js"></script><h1>Проверка HSV</h1><button id="run">Проверить HSV</button><pre id="result"></pre><script>
const tasks=TASKS;
document.querySelector('#run').onclick=async()=>{let failures=0,checks=0;const out=document.querySelector('#result');document.querySelector('#run').disabled=true;for(const t of tasks){try{const {tests}=await(await fetch('../browser/tests/image/'+t.slug+'/index.json')).json();for(const [label,code,ok] of [['correct',t.solution,true],['blank',"import cv2\\nimport numpy as np\\na=cv2.imread('input.png')\\ncv2.imwrite('output.png', np.zeros(a.shape[:2], dtype=np.uint8))",false]]){const results=await BrowserPython.run({code,tests});checks+=results.length;const bad=results.filter(r=>ok?r.result!=='ok':r.result==='ok'||r.result==='skipped');failures+=bad.length;out.textContent+=(bad.length?'FAIL ':'PASS ')+t.slug+' '+label+' '+JSON.stringify(results.map(r=>r.result))+'\\n';}}catch(e){failures++;out.textContent+='ERROR '+t.slug+' '+e.message+'\\n';}}out.textContent+='DONE '+checks+' checks, '+failures+' failures';};</script>'''
(root/'dist/pages/audit/hsv-tasks.html').write_text(html.replace('TASKS',json.dumps(tasks).replace('<','\\u003c')))
