(() => {
const el=id=>document.getElementById(id),rows=document.querySelector('tbody');
let secret='',people=[],catalog={},generation=0,idle;
const changes=new Map();
let saving=false;
function controls(){
 const editing=changes.size>0;
 for(const id of ['day','group','refresh'])el(id).disabled=editing||saving;
 el('save').disabled=!editing||saving;
 el('discard').hidden=!editing;
 el('discard').disabled=saving;
 el('pending').textContent=editing?'Несохранённых изменений: '+changes.size:'';
}
const day=()=>new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Moscow'}).format(new Date());
const request=(action,data={})=>PTClass.post({op:'journal',action,key:secret,...data});
function lock(){
 generation++;changes.clear();saving=false;controls();secret='';people=[];rows.replaceChildren();el('counts').textContent='';
 el('panel').hidden=true;el('login').hidden=false;el('key').value='';el('status').textContent='';
}
function touch(){clearTimeout(idle);idle=setTimeout(lock,600000);}
for(const event of ['keydown','pointerdown','wheel'])window.addEventListener(event,touch,{passive:true});
window.addEventListener('pagehide',lock);el('lock').onclick=lock;
async function refresh(){
 if(!secret||!people.length||saving||changes.size)return;
 const ticket=++generation,selectedDay=el('day').value,group=el('group').value;
 const visible=people.filter(p=>!group||p.group===group);
 const ids=[...new Set(visible.flatMap(p=>p.ids))];
 try{
 const {students,attendance}=await request('overview',{ids,day:selectedDay});
 if(ticket!==generation||saving||changes.size)return;
 const marked=new Set(attendance.map(([m,g])=>m+g));rows.replaceChildren();let active=0,present=0;
 for(const p of visible){
  const matches=p.ids.filter(id=>students[id]),id=matches[0];
  const ambiguous=matches.length>1||(id&&people.some(q=>q.member!==p.member&&q.ids.includes(id)));
  const record=!ambiguous&&students[id],tasks=record?.tasks||[];
  const tr=rows.insertRow();
  for(const value of [p.name,p.group,ambiguous?'Уточните класс':record?p.ids.indexOf(id)+1:'—',record?.solved??'—',record?.started??'—'])tr.insertCell().textContent=value;
  const work=tr.insertCell();if(tasks.length){active++;const details=document.createElement('details'),title=document.createElement('summary');title.textContent='Работал · '+tasks.length;details.append(title);for(const task of tasks){const line=document.createElement('div');line.textContent=catalog[task]?.title||task;details.append(line);}work.append(details);}else work.textContent=record?'Нет попыток':'Нет данных';
  const box=document.createElement('input');box.type='checkbox';box.checked=marked.has(p.member+p.group);if(box.checked)present++;box.setAttribute('aria-label','Явка: '+p.name);tr.insertCell().append(box);
  box.onchange=()=>{
   const key=p.member+p.group;
   if(box.checked===marked.has(key))changes.delete(key);
   else changes.set(key,{member:p.member,group:p.group,present:box.checked});
   controls();
  };
 }
 el('counts').textContent='Учеников: '+visible.length+' · Работали: '+active+' · Явка подтверждена: '+present;
 el('status').textContent='Обновлено '+new Date().toLocaleTimeString('ru');
 }catch(e){if(ticket===generation)el('status').textContent=e.message;}
}
el('login').onsubmit=async event=>{
 event.preventDefault();const ticket=++generation;secret=el('key').value.trim();touch();
 try{
 const payload=await request('roster'),bytes=s=>Uint8Array.from(atob(s),c=>c.charCodeAt(0));
 const key=await crypto.subtle.importKey('raw',await crypto.subtle.digest('SHA-256',new TextEncoder().encode('roster-v1:'+secret)),'AES-GCM',false,['decrypt']);
 const plain=await crypto.subtle.decrypt({name:'AES-GCM',iv:bytes(payload.iv)},key,bytes(payload.data));
 const prepared=await Promise.all(JSON.parse(new TextDecoder().decode(plain)).map(async p=>{const [family,given]=p.name.split(/\s+/);return {...p,ids:await Promise.all(Array.from({length:11},(_,i)=>PTClass.identity(family,given,i+1)))};}));
 catalog=await (await fetch('catalog.json')).json();if(ticket!==generation)return;
 people=prepared;el('key').value='';el('day').value=day();el('login').hidden=true;el('panel').hidden=false;await refresh();
 }catch(e){if(ticket===generation){secret='';el('status').textContent=e.message;}}
};
el('discard').onclick=()=>{changes.clear();controls();rows.replaceChildren();refresh();};
el('save').onclick=async()=>{
 if(saving||!changes.size)return;
 const ticket=++generation;
 saving=true;controls();rows.querySelectorAll('input').forEach(box=>box.disabled=true);
 try{
  await request('attendance_list',{day:el('day').value,changes:[...changes.values()]});
  if(ticket!==generation)return;
  changes.clear();el('status').textContent='Явка сохранена.';
 }catch(e){if(ticket===generation)el('status').textContent=e.message;}
 finally{if(ticket===generation){saving=false;controls();rows.querySelectorAll('input').forEach(box=>box.disabled=false);if(!changes.size)await refresh();}}
};
el('refresh').onclick=refresh;
el('group').onchange=el('day').onchange=()=>{rows.replaceChildren();el('counts').textContent='';refresh();};
setInterval(()=>{if(!document.hidden)refresh();},30000);
})();
