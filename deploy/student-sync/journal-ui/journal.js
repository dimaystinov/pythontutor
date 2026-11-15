(() => {
const get=id=>document.getElementById(id),date=value=>new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Moscow'}).format(new Date(value));
get('day').value=date(Date.now());
const catalog=fetch('catalog.json').then(r=>r.json());
let roster=[],generation=0,timer;
function lock(){
 generation++;roster=[];document.querySelector('form').reset();get('key').value='';get('roster').value='';
 get('file').value='';get('group').length=1;get('day').value=date(Date.now());
 document.querySelector('tbody').replaceChildren();get('note').textContent='';
}
function activity(){clearTimeout(timer);timer=setTimeout(lock,600000);}
for(const event of ['keydown','pointerdown','wheel'])window.addEventListener(event,activity,{passive:true});
window.addEventListener('pagehide',lock);activity();
get('file').onchange=async()=>{
 roster=[];get('group').length=1;
 try{
  const file=get('file').files[0];if(!file)return;
  if(file.size>500000)throw Error('Список слишком большой.');
  const lines=(await file.text()).trim().split(/\r?\n/);
  const members=new Map();let section='';
  for(const line of lines){
   if(!line.trim()||line.startsWith('ФИО;Идентификатор'))continue;
   const [name,id,groups]=line.split(';');
   if(/^\d+ группа$/.test(name)){section=id;continue;}
   if(!name||!/^[-a-f0-9]{36}$/i.test(id)||!(groups||section))throw Error('Проверьте строки и названия групп в CSV.');
   const person=members.get(id)||{name,groups:[]};
   person.groups=[...new Set(person.groups.concat(groups?groups.split(' | '):section))];members.set(id,person);
  }
  roster=[...members.values()].sort((a,b)=>a.name.localeCompare(b.name,'ru'));
  const number=g=>Number(g.match(/группа (\d+)/i)?.[1]||0);
  for(const group of [...new Set(roster.flatMap(p=>p.groups))].sort((a,b)=>number(a)-number(b)))get('group').add(new Option(group,group));
  get('note').textContent='Загружено участников: '+roster.length;
 }catch(err){roster=[];get('note').textContent=err.message;}
};
document.querySelector('form').onsubmit=async e=>{
 e.preventDefault();const requestGeneration=++generation;const table=document.querySelector('tbody');table.replaceChildren();
 try{
 const people=[];
 for(const p of roster.filter(p=>!get('group').value||p.groups.includes(get('group').value))){
  const [surname,given]=p.name.split(/\s+/);
  people.push({...p, candidates:await Promise.all(Array.from({length:11},async(_,i)=>({id:await PTClass.identity(surname,given,i+1),grade:i+1})))});
 }
 for(const line of get('roster').value.trim().split(/\n+/).filter(Boolean)){
  const fields=line.trim().split(/[\s;,]+/),grade=/^\d+$/.test(fields.at(-1))?fields.pop():get('grade').value;
  if(fields.length<2||fields.length>3)throw Error('Проверьте строку: '+line);
  const [surname,given]=fields;people.push({name:surname+' '+given,groups:[],candidates:[{grade,id:await PTClass.identity(surname,given,grade)}]});
 }
 if(!people.length)throw Error('Введите список или выберите CSV.');
 const students={},ids=[...new Set(people.flatMap(p=>p.candidates.map(c=>c.id)))];
 for(let i=0;i<ids.length;i+=400)Object.assign(students,(await PTClass.post({op:'journal',key:get('key').value,ids:ids.slice(i,i+400)})).students);
 const tasks=await catalog;if(requestGeneration!==generation)return;
 for(const p of people){
  const matches=p.candidates.filter(c=>students[c.id]),match=matches.length===1&&matches[0];
  const ambiguous=matches.length>1||(match&&people.some(other=>other!==p&&other.candidates.some(c=>c.id===match.id)));
  const records=match&&!ambiguous?students[match.id]:undefined,tr=table.insertRow(),solved=records?.filter(r=>r.solved).length;
  const attempts=records?.filter(r=>date(r.time)===get('day').value).sort((a,b)=>b.time.localeCompare(a.time));
  for(const value of [p.name,ambiguous?'Уточните класс':match?.grade||'—',p.groups.join(', ')||'—',records?solved:'Нет данных',records?records.length-solved:'—',attempts?.map(r=>(tasks[r.kind+':'+r.slug]?.title||r.slug)+(r.solved?' ✓':' · в работе')).join(', ')||'—'])tr.insertCell().textContent=value;
 }
 get('note').textContent='Обновлено '+new Date().toLocaleTimeString('ru');
 }catch(err){get('note').textContent=err.message==='Неверный пароль.'?'Проверьте ключ преподавателя.':err.message;}
};
})();
