(function(){
'use strict';
const $=id=>document.getElementById(id),note=$('pwa-status');
const say=text=>{if(note)note.textContent=text;};
let registration,installEvent;
async function message(data,progress){registration=registration||await navigator.serviceWorker.ready;return new Promise((resolve,reject)=>{const channel=new MessageChannel();channel.port1.onmessage=({data:r})=>{if(r.error){channel.port1.close();reject(Error(r.error));}else if(r.done!==undefined)progress?.(r);else{channel.port1.close();resolve(r);}};registration.active.postMessage(data,[channel.port2]);});}
window.addEventListener('beforeinstallprompt',event=>{event.preventDefault();installEvent=event;if($('pwa-install'))$('pwa-install').hidden=false;});
async function install(){if(!installEvent){if(!note){location.href='/pythontutor/pwa/';return;}say('Используйте меню браузера: «Установить приложение» / «Добавить на экран Домой». Если приложение уже установлено, откройте его значок.');return;}await installEvent.prompt();installEvent=null;}
$('pwa-install')?.addEventListener('click',install);$('pwa-install-nav')?.addEventListener('click',install);
window.addEventListener('appinstalled',()=>{if($('pwa-install-nav'))$('pwa-install-nav').hidden=true;say('Приложение установлено. Скачайте курс, чтобы работать без сети.');});
async function refresh(){const state=await message({type:'status'});if($('pwa-open'))$('pwa-open').disabled=!state.ready;say(state.ready?'Курс скачан: '+state.ready.files+' файлов. Можно работать без интернета.':'Курс ещё не скачан. Подключитесь к сети и нажмите кнопку загрузки.');}
if('serviceWorker' in navigator){navigator.serviceWorker.register('/pythontutor/sw.js',{scope:'/pythontutor/'}).then(async r=>{registration=r;await navigator.serviceWorker.ready;await refresh();}).catch(e=>say('Не удалось включить PWA: '+e.message));}else say('Для PWA нужен современный браузер и HTTPS или localhost.');
$('pwa-download')?.addEventListener('click',async()=>{
 $('pwa-download').disabled=true;$('pwa-progress').hidden=false;
 try{await navigator.storage?.persist?.();await message({type:'download'},r=>{say('Скачиваем курс: '+r.done+' из '+r.total+' файлов');$('pwa-progress').value=r.done/r.total*100;});await refresh();}
 catch(e){say(e.message+' Предыдущая полная загрузка сохранена.');}
 finally{$('pwa-download').disabled=false;$('pwa-progress').hidden=true;}
});
$('pwa-open')?.addEventListener('click',async()=>{await message({type:'mode',local:true});location.href='/pythontutor/';});
$('pwa-online')?.addEventListener('click',async()=>{await message({type:'mode',local:false});location.href='/pythontutor/';});
async function progress(){if(!$('pwa-results'))return;const entries=await TutorDevice.list();$('pwa-results').textContent=entries.length?'':'На этом устройстве пока нет решений для текущего профиля.';for(const r of entries){const p=document.createElement('p');p.textContent=(r.solved?'✓ Решено: ':'В работе: ')+r.slug+' · '+new Date(r.time).toLocaleString();$('pwa-results').append(p);}}
progress().catch(()=>say('Хранилище браузера недоступно. Разрешите сохранение данных сайта.'));
const backupKey=key=>/^(problem-draft:|image-draft:|tutor-local-chat:)/.test(key)||['tutor-ai-model','tutor-panel-width','lesson-menu-open','tutor-hsv-settings'].includes(key);
function localBackup(){const data={};for(let i=0;i<localStorage.length;i++){const key=localStorage.key(i);if(backupKey(key))data[key]=localStorage.getItem(key);}return data;}
$('pwa-export')?.addEventListener('click',async()=>{const url=URL.createObjectURL(new Blob([JSON.stringify({version:2,solutions:await TutorDevice.list(),preferences:localBackup()},null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='pythontutor-progress.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
$('pwa-import')?.addEventListener('change',async event=>{try{const file=event.target.files[0];if(!file)return;if(file.size>32*1024*1024)throw Error('Копия больше 32 МБ.');const data=JSON.parse(await file.text());if(![1,2].includes(data.version)||!Array.isArray(data.solutions)||data.solutions.length>1000)throw Error('Неверный формат копии.');for(const r of data.solutions){if(!['problem','image'].includes(r.kind)||!/^[-\w]+$/.test(r.slug)||typeof r.code!=='string'||r.code.length>65536||!['ok','error'].includes(r.result?.status))throw Error('Некорректное решение.');}if(data.version===2){if(!data.preferences||typeof data.preferences!=='object'||Array.isArray(data.preferences))throw Error('Неверные настройки копии.');for(const [key,value] of Object.entries(data.preferences)){if(!backupKey(key)||typeof value!=='string'||value.length>2000000)throw Error('Некорректные локальные данные.');}}for(const r of data.solutions)await TutorDevice.save(r.kind,r.slug,r.code,r.result,typeof r.acceptedCode==='string'?r.acceptedCode:'');if(data.version===2)for(const [key,value] of Object.entries(data.preferences))localStorage.setItem(key,value);await progress();say('Данные восстановлены в текущий локальный профиль.');}catch(e){say(e.message);}});
// Other open task tabs must stop autosaving the previous student's drafts.
window.addEventListener('storage',event=>{
 if(event.key==='tutor-progress-reset:'+TutorDevice.owner())location.reload();
});
$('pwa-reset')?.addEventListener('click',()=>{$('pwa-reset-confirm').hidden=false;$('pwa-reset-cancel').focus();});
$('pwa-reset-cancel')?.addEventListener('click',()=>{$('pwa-reset-confirm').hidden=true;$('pwa-reset').focus();});
$('pwa-reset-accept')?.addEventListener('click',async()=>{
 $('pwa-reset-accept').disabled=true;
 try{await TutorDevice.reset();location.reload();}
 catch(e){$('pwa-reset-message').textContent='Не удалось полностью очистить прогресс: '+e.message;$('pwa-reset-accept').disabled=false;}
});
const local=document.querySelector('meta[name=local-page]')?.content==='yes';
async function restoreProgress(){
 const entries=await TutorDevice.list().catch(()=>[]);
 const states=new Map(entries.map(r=>[r.kind+':'+r.slug,r]));
 try {
  const prefix='problem-draft:'+TutorDevice.owner()+':';
  for(let i=0;i<localStorage.length;i++){
   const key=localStorage.key(i);
   if(!key.startsWith(prefix))continue;
   try {
    const draft=JSON.parse(localStorage.getItem(key)),slug=key.slice(prefix.length);
    if(draft?.started&&!states.has('problem:'+slug))states.set('problem:'+slug,{kind:'problem',slug,solved:false});
   } catch(e) { /* Ignore a damaged draft without losing other progress. */ }
  }
 } catch(e) { /* Browser storage may be disabled. */ }
 const article=document.querySelector('[data-local-article]');
 if(article){const record=await TutorDevice.get(article.dataset.localArticle,article.dataset.slug);if(record?.solved){article.hidden=false;$('local-knowledge-notice').hidden=true;$('knowledge-own-code').textContent=record.acceptedCode||record.code;}}
 for(const r of states.values()){
  const ending=r.kind==='image'?'/pythontutor/images/'+r.slug+'/':'/problems/'+r.slug+'/';
  for(const a of document.querySelectorAll('a[href]')){
   if(!a.getAttribute('href').endsWith(ending))continue;
   a.classList.remove('text-success');
   if(a.matches('.lesson_sections .problems_link li > a')){
    const solved=r.solved||a.parentElement.classList.contains('solved');
    a.parentElement.classList.remove('unsolved','accepted');
    a.parentElement.classList.add(solved?'solved':'unsolved');
    a.title=solved?'Задача решена':'Задача начата, но ещё не решена';
   }
  }
  const slug=window.problem_name||document.getElementById('image-task')?.dataset.slug;
  if(r.solved&&slug===r.slug&&$('knowledge-unlock'))$('knowledge-unlock').hidden=false;
 }
}
restoreProgress().catch(()=>{});
window.addEventListener('tutor-progress-changed',()=>restoreProgress().catch(()=>{}));
if(local){document.querySelectorAll('a[href^="/accounts"],a.original-teacher').forEach(a=>{a.title='Нужен интернет';});}
})();
