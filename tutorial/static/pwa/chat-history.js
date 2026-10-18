(function(){
'use strict';
window.TutorChatHistory={create(storage,owner){
 const prefix='tutor-local-chat:'+owner+':',key=prefix+'shared';
 const keys=()=>Object.keys(storage).filter(k=>k.startsWith(prefix));
 const read=k=>{try{const rows=JSON.parse(storage.getItem(k)||'[]');return Array.isArray(rows)?rows.filter(t=>t&&typeof t.question==='string'&&typeof t.answer==='string'):[];}catch(_){return [];}};
 function list(){
  const rows=read(key),legacy=keys().filter(k=>k!==key),seen=new Set(rows.filter(t=>t.id).map(t=>t.id));
  for(const k of legacy)for(const t of read(k)){if(t.id&&seen.has(t.id))continue;rows.push({...t,task:t.task||k.slice(prefix.length)});if(t.id)seen.add(t.id);}
  if(legacy.length){storage.setItem(key,JSON.stringify(rows));legacy.forEach(k=>storage.removeItem(k));}
  return rows;
 }
 return {list,append(turn,task){const rows=list();rows.push({...turn,task,createdAt:Date.now()});storage.setItem(key,JSON.stringify(rows));return rows;},clear(){keys().forEach(k=>storage.removeItem(k));}};
}};
})();
