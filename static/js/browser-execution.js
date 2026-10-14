(function(){
'use strict';
if(document.querySelector('meta[name=execution-mode]')?.content!=='browser')return;
function status(text){document.querySelectorAll('[data-browser-status]').forEach(e=>e.textContent=text);}
function runJob(job){return new Promise((resolve,reject)=>{
 const worker=new Worker('/pythontutor/static/browser/worker.mjs',{type:'module'});
 let timer,index=0;
 function dispose(){clearTimeout(timer);worker.terminate();}
 function fail(error){dispose();status(error);reject(new Error(error));}
 function deadline(ms,execution=false){clearTimeout(timer);timer=setTimeout(()=>{
   if(!execution){fail('Не удалось загрузить Python. Проверьте подключение и повторите запуск.');return;}
   dispose();status('Выполнение остановлено по лимиту времени.');
   const result={result:'realtime_limited',stdout:'',stderr:''};
   resolve(job.tests?job.tests.map((_,i)=>i===index?result:{result:'skipped',stdout:''}):result);
 },ms);}
 function receive(event){
  const data=event.data;
  if(data.phase==='loading'){status('Загружаем Python в браузер…');return;}
  if(data.phase==='executing'){index=data.index;status('Выполняется в вашем браузере'+(job.tests?' · тест '+(index+1)+'/'+data.total:''));deadline(8000,true);return;}
  if(data.error){fail('Ошибка среды Python: '+data.error);return;}
  if(data.result){dispose();status('Python выполняется на вашем устройстве.');resolve(data.result);}
 }
 worker.onmessage=receive;worker.onerror=e=>fail(e.message||'Не удалось запустить среду Python.');deadline(120000);worker.postMessage(job);
});}
let queue=Promise.resolve(),lastRun=null;
window.addEventListener?.('storage',event=>{if(event.key?.startsWith('tutor-progress-reset:'))lastRun=null;});
function remember(job,result){
 const list=Array.isArray(result)?result:[result];
 const index=list.findIndex(r=>r.result!=='ok'&&r.result!=='skipped');
 const item=list[index<0?0:index]||{};
 lastRun={code:job.code,checked:!!job.tests,total:list.length,passed:list.filter(r=>r.result==='ok').length,
  result:item.result,exception:item.exception||null,stderr:String(item.stderr||'').slice(0,1500),
  stdout:String(item.stdout||'').slice(0,1500),test:index<0?null:index+1,
  stdin:String((job.tests?.[index]?.stdin)??job.stdin??'').slice(0,800),
  expected:typeof job.tests?.[index]?.answer==='string'?job.tests[index].answer.slice(0,800):null};
}

function run(job){lastRun=null;const next=queue.then(()=>runJob(job));queue=next.catch(()=>{});return next.then(result=>{remember(job,result);return result;});}
async function submit(kind,slug,code){
 const response=await fetch('/pythontutor/browser/tests/'+kind+'/'+encodeURIComponent(slug)+'/index.json');
 if(!response.ok||response.redirected)throw new Error('Тесты недоступны. Скачайте курс для работы без интернета.');
 const {tests}=await response.json();const results=await run({code,tests});
 const verdicts=results.map(r=>r.result);
 const result={status:verdicts.every(v=>v==='ok')?'ok':'error',tests:verdicts,execution_source:'browser',local:true};
 try{await window.TutorDevice.save(kind,slug,code,result);}catch(e){result.storage_error=true;status('Проверка завершена, но сохранить решение не удалось. Освободите место на устройстве.');}
 // A network/account failure must never discard the locally graded result.
 const owner=document.querySelector('meta[name=learner-id]')?.content;
 if(owner&&owner!=='local'&&navigator.onLine){
  try{
   const saved=await fetch('/pythontutor/browser/submit/'+kind+'/'+encodeURIComponent(slug)+'/',{method:'POST',signal:AbortSignal.timeout(4000),headers:{'Content-Type':'application/json','X-CSRFToken':document.querySelector('meta[name=csrf-token]').content},body:JSON.stringify({code,results:verdicts.map(result=>({result}))})});
   if(saved.ok&&!saved.redirected)result.synced=true;
  }catch(_){}
 }
 result.outputs=results.map(r=>typeof r.stdout==='string'?r.stdout:'');
 return result;
}
window.BrowserPython={run,submit,lastRun:()=>window.TutorDevice?.isCurrent?.()===false?null:lastRun};
document.addEventListener('DOMContentLoaded',()=>{
 if(!document.querySelector('#visualizer,.visualizer,#image-task'))return;
 const note=document.createElement('p');note.dataset.browserStatus='';note.setAttribute('role','status');note.className='text-muted';note.textContent='Python выполняется на вашем устройстве. При первом запуске загрузится среда Python.';
 const target=document.querySelector('#visualizer,#image-task');
 if(target)target.before(note);else document.querySelector('.main')?.prepend(note);
});
})();
