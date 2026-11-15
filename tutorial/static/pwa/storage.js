(function(){
'use strict';
const learner=window.TutorNative?.profile?.id||document.querySelector('meta[name=learner-id]')?.content||'local';
const owner=()=>learner;
const resetKey='tutor-progress-reset:'+owner();
const generation=()=>{try{return localStorage.getItem(resetKey);}catch(e){return null;}};
const pageGeneration=generation();
const isCurrent=()=>pageGeneration===generation() && (!window.PTClass || window.PTClass.valid());
const requireCurrent=()=>{if(!isCurrent())throw Error('Прогресс очищен. Откройте задачу заново.');};
let connection;
function db(){return connection||(connection=new Promise((resolve,reject)=>{const r=indexedDB.open('tutor-device-progress',1);r.onupgradeneeded=()=>r.result.createObjectStore('solutions',{keyPath:'key'});r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);}));}
async function query(mode,action){const d=await db();return new Promise((resolve,reject)=>{const tx=d.transaction('solutions',mode),r=action(tx.objectStore('solutions'));tx.oncomplete=()=>resolve(r.result);tx.onerror=()=>reject(tx.error);tx.onabort=()=>reject(tx.error);});}
async function get(kind,slug){if(window.TutorNative)return (await list()).find(r=>r.kind===kind&&r.slug===slug);return query('readonly',s=>s.get(owner()+':'+kind+':'+slug));}
async function save(kind,slug,code,result,acceptedCode){requireCurrent();const previous=await get(kind,slug);requireCurrent();const item={key:owner()+':'+kind+':'+slug,owner:owner(),kind,slug,code,result,solved:previous?.solved||result.status==='ok'||!!acceptedCode,acceptedCode:result.status==='ok'?code:(previous?.acceptedCode||acceptedCode||''),time:new Date().toISOString()};if(window.TutorNative)await window.TutorNative.invoke('save_solution',{data:item});else await query('readwrite',s=>{requireCurrent();return s.put(item);});window.dispatchEvent(new Event('tutor-progress-changed'));return item;}
async function list(){if(window.TutorNative)return window.TutorNative.invoke('solutions');return (await query('readonly',s=>s.getAll())).filter(r=>r.owner===owner());}
async function reset(){
 // Invalidate old editors before any asynchronous deletion starts.
 localStorage.setItem(resetKey,Date.now()+':'+Math.random());
 if(window.TutorNative){
  await window.TutorNative.invoke('reset_progress');
 }else{
 const d=await db();
 await new Promise((resolve,reject)=>{
  const tx=d.transaction('solutions','readwrite'),s=tx.objectStore('solutions');
  if(window.PTClass && owner()!=='local'){const marker=s.get('sync:'+owner());marker.onsuccess=()=>s.put({...marker.result,key:'sync:'+owner(),reset:(marker.result?.reset||0)+1});}
  const records=s.getAll();
  records.onsuccess=()=>{for(const r of records.result)if(r.owner===owner())s.delete(r.key);};
  tx.oncomplete=resolve;tx.onerror=()=>reject(tx.error);tx.onabort=()=>reject(tx.error);
 });
 }
 const prefixes=['problem-draft:','image-draft:','tutor-local-chat:'].map(p=>p+owner()+':');
 const keys=[];
 for(let i=0;i<localStorage.length;i++){const key=localStorage.key(i);if(prefixes.some(p=>key.startsWith(p)))keys.push(key);}
 keys.forEach(key=>localStorage.removeItem(key));
 localStorage.removeItem('tutor-hsv-settings');
 localStorage.setItem('tutor-progress-reset-done:'+owner(),generation());
 if(window.TutorNative)window.dispatchEvent(new Event('tutor-progress-changed'));
}
async function syncSnapshot(){
 requireCurrent();
 const all=await query('readonly',s=>s.getAll()), meta=all.find(r=>r.key==='sync:'+owner());
 return {items:all.filter(r=>r.owner===owner()),epoch:meta?.epoch,reset:meta?.reset||0};
}
async function applySync(before,reply,epoch){
 requireCurrent();
 const d=await db(),key='sync:'+owner();
 return new Promise((resolve,reject)=>{
  const tx=d.transaction('solutions','readwrite'),store=tx.objectStore('solutions'),request=store.getAll();
  request.onsuccess=()=>{
   if(!isCurrent())return;
   const rows=request.result,meta=rows.find(r=>r.key===key);
   if(meta?.epoch!==before.epoch||(meta?.reset||0)!==before.reset)return;
   const old=new Map(before.items.map(r=>[r.key,r]));
   const same=k=>old.get(k)?.time===rows.find(r=>r.key===k)?.time;
   if(reply.epoch!==epoch)for(const r of before.items)if(same(r.key))store.delete(r.key);
   for(const r of reply.items){
    const k=owner()+':'+r.kind+':'+r.slug;
    if(same(k))store.put({...r,key:k,owner:owner(),result:old.get(k)?.time===r.time?old.get(k).result:{status:r.solved?'ok':'error'}});
   }
   store.put({key,epoch:reply.epoch,reset:0});
  };
  tx.oncomplete=resolve;tx.onerror=()=>reject(tx.error);tx.onabort=()=>reject(tx.error);
 });
}
window.TutorDevice={owner,get,save,list,reset,isCurrent,syncSnapshot,applySync};
})();
