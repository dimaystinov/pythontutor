(function(){
'use strict';
const owner=()=>document.querySelector('meta[name=learner-id]')?.content||'local';
let connection;
function db(){return connection||(connection=new Promise((resolve,reject)=>{const r=indexedDB.open('tutor-device-progress',1);r.onupgradeneeded=()=>r.result.createObjectStore('solutions',{keyPath:'key'});r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);}));}
async function query(mode,action){const d=await db();return new Promise((resolve,reject)=>{const tx=d.transaction('solutions',mode),r=action(tx.objectStore('solutions'));tx.oncomplete=()=>resolve(r.result);tx.onerror=()=>reject(tx.error);tx.onabort=()=>reject(tx.error);});}
async function get(kind,slug){return query('readonly',s=>s.get(owner()+':'+kind+':'+slug));}
async function save(kind,slug,code,result,acceptedCode){const previous=await get(kind,slug);const item={key:owner()+':'+kind+':'+slug,owner:owner(),kind,slug,code,result,solved:previous?.solved||result.status==='ok'||!!acceptedCode,acceptedCode:result.status==='ok'?code:(previous?.acceptedCode||acceptedCode||''),time:new Date().toISOString()};await query('readwrite',s=>s.put(item));window.dispatchEvent(new Event('tutor-progress-changed'));return item;}
async function list(){return (await query('readonly',s=>s.getAll())).filter(r=>r.owner===owner());}
window.TutorDevice={owner,get,save,list};
})();
