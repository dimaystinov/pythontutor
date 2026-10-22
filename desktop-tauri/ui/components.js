(function(){
'use strict';
if(!window.__TAURI__)return;
window.addEventListener('DOMContentLoaded',async()=>{
 const invoke=(name,args)=>window.TutorNative.invoke(name,args);
 const components=[
  {id:'qwen7b',name:'Qwen Coder 7B',model:'Qwen2.5-Coder-7B-Instruct-q4f16_1-MLC',note:'Работает без интернета. Требуется совместимая видеокарта и около 5 ГБ видеопамяти.',status:()=>invoke('model_status'),install:cb=>window.TutorModelAssets.ensure('qwen7b',cb),cancel:()=>invoke('cancel_model')},
  {id:'opencode',name:'OpenCode',model:'opencode-local',note:'Ответы через интернет. Доступность бесплатных моделей зависит от провайдера.',status:()=>invoke('cli_status'),install:async cb=>{const off=await window.__TAURI__.event.listen('cli-install-progress',e=>cb(e.payload.text));try{await invoke('install_cli');}finally{off();}},cancel:()=>invoke('cancel_cli_install')},
  {id:'localspeech',name:'Голосовой ввод LocalSpeech',note:'Распознавание русской речи на устройстве.',status:async()=>({installed:await window.TutorSpeech.ready(),bytes:43*1048576}),install:cb=>window.TutorSpeech.prepare(cb),cancel:()=>window.TutorSpeech.cancel()}
 ];
 const select=document.getElementById('tutor-model');
 const options=select?[...select.options].filter(o=>components.some(c=>c.model===o.value)):[];
 options.forEach(o=>o.remove());
 const heading=document.getElementById('settings-assistant');
 const section=heading?.closest('section');
 if(section){
  [...section.children].forEach(e=>{if(e!==heading)e.hidden=true;});
  const intro=document.createElement('p');intro.textContent='Встроенный консультант · установлен. Работает без скачиваний.';section.append(intro);
 }
 const settingsLink=document.createElement('a');settingsLink.href='/pythontutor/pwa/#settings-assistant';settingsLink.textContent='Установить дополнительные компоненты';
 select?.after(settingsLink);
 for(const c of components){
  let note,download,remove,bar,cancel,busy=false;
  if(section){
   const card=document.createElement('section');card.style.cssText='padding:16px 0;border-top:1px solid #dce6ee';
   const title=document.createElement('h3');title.textContent=c.name;card.append(title);
   const description=document.createElement('p');description.textContent=c.note;card.append(description);
   note=document.createElement('p');note.setAttribute('role','status');note.textContent='Проверка…';card.append(note);
   download=document.createElement('button');download.textContent='Скачать';download.className='btn btn-primary';download.disabled=true;
   remove=document.createElement('button');remove.textContent='Удалить';remove.className='btn btn-default';remove.hidden=true;
   cancel=document.createElement('button');cancel.textContent='Отменить';cancel.hidden=true;cancel.onclick=c.cancel;
   bar=document.createElement('progress');bar.max=100;bar.hidden=true;bar.style.width='100%';
   card.append(download,remove,cancel,bar);section.append(card);
   const progress=text=>{note.textContent=String(text);bar.hidden=false;const n=String(text).match(/(\d+)%/);if(n)bar.value=Number(n[1]);else bar.removeAttribute('value');};
   download.onclick=async()=>{busy=true;download.disabled=true;cancel.hidden=false;progress('Подключение…');try{await c.install(progress);await refresh();}catch(e){note.textContent='Ошибка загрузки: '+(e.message||e);download.textContent='Повторить';}finally{busy=false;download.disabled=false;cancel.hidden=true;bar.hidden=true;}};
   remove.onclick=async()=>{remove.disabled=true;try{await window.TutorModelAssets.remove(c.id);await refresh();}catch(e){note.textContent=String(e.message||e);}finally{remove.disabled=false;}};
  }
  async function refresh(){
   try{
    const state=await c.status();
    const option=options.find(o=>o.value===c.model);
    if(option){if(state.installed){if(!option.parentNode)select.append(option);const saved=localStorage.getItem('tutor-ai-model');if(saved===c.model)select.value=c.model;}else{const selected=select.value===c.model;option.remove();if(selected){select.value='guided';select.dispatchEvent(new Event('change'));}}}
    if(note){note.textContent=(state.installed?'Установлен':'Не установлен')+(state.bytes?' · '+(state.bytes/1048576).toFixed(0)+' МБ':'');download.hidden=state.installed;remove.hidden=!state.installed;download.disabled=false;}
   }catch(e){if(note){note.textContent='Не удалось проверить: '+(e.message||e);download.disabled=true;}}
  }
  await refresh();
  window.addEventListener('tutor-component-removed',e=>{if(e.detail===c.id&&!busy)refresh();});
 }
 if(select&&!select.value)select.value='guided';
 window.dispatchEvent(new Event('tutor-components-ready'));
});
})();
