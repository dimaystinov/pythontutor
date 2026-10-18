/* Download optional components directly into verified local storage. */
(function () {
'use strict';
const base = new URL('../models/', document.currentScript.src);
const manifestURL = new URL('model-assets.json?v=cors20261017', document.currentScript.src);
let manifestPromise,installedPromise,downloadController;
const downloadModuleURL=new URL("model-download.mjs?v=cors20261017",document.currentScript.src).href;
const installed=()=>installedPromise ||= fetch(new URL('installed.json',base),{cache:'no-store'}).then(r=>r.ok?r.json():{groups:[]}).catch(()=>({groups:[]}));
const manifest = () => manifestPromise ||= fetch(manifestURL).then(r => {if (!r.ok) throw Error('Не удалось прочитать список файлов ИИ.'); return r.json();});
const target = item => new URL(item.path.replace('ndarray-cache.json','tensor-cache.json'), base).href;
async function present(item) {
 const response = await (await caches.open(item.cache)).match(target(item));
 return response?.headers.get('x-tutor-sha256') === item.sha256;
}
async function ready(group) {
 if((await installed()).groups?.includes(group))return true;
 const data = await manifest();
 for (const item of data.files.filter(f => f.group === group)) if (!await present(item)) return false;
 return true;
}
async function ensure(group, progress = () => {}) {
 if(window.TutorNative && group==='qwen7b'){
  const unlisten=await window.__TAURI__.event.listen('model-progress',event=>progress(event.payload));
  try{
   const directory=await window.TutorNative.invoke('prepare_model');
   window.TutorModelAssets.base=window.__TAURI__.core.convertFileSrc(directory)+'/';
   // Migrate only this model's old web cache, after Rust verified the disk copy.
   if(typeof caches!=='undefined'){
    for(const name of await caches.keys()){
     if(!['webllm/model','webllm/config','webllm/wasm'].includes(name))continue;
     const cache=await caches.open(name);
     for(const request of await cache.keys()){
      const path=new URL(request.url).pathname;
      if(path.includes('/qwen7b/')||path.includes('/Qwen2.5-Coder-7B-Instruct-q4f16_1-MLC/'))await cache.delete(request);
     }
    }
   }
   return;
  }finally{unlisten();}
 }
 if (await ready(group)) return;
 if(group==='qwen7b'){
  if(downloadController)throw Error('Дождитесь загрузки модели.');
  const controller=downloadController=new AbortController();
  try{
   const {downloadModel}=await import(downloadModuleURL);
   await downloadModel((await manifest()).files.filter(f=>f.group===group),{present,progress,signal:controller.signal,save:async(item,bytes)=>{
    const cache=await caches.open(item.cache);
    await cache.put(target(item),new Response(bytes,{headers:{'Content-Type':item.path.endsWith('.json')?'application/json':'application/octet-stream','x-tutor-sha256':item.sha256}}));
   }});
   return;
  }finally{downloadController=null;}
 }
 window.dispatchEvent(new CustomEvent('tutor-model-needed', {detail: group}));
 throw Error('Для голосового ввода установите LocalSpeech в настройках помощника.');
}
const decode = bytes => new TextDecoder().decode(bytes).replace(/\0.*$/s, '').trim();
function headerInfo(bytes) {
 if (bytes.every(b => b === 0)) return null;
 const stored = parseInt(decode(bytes.subarray(148,156)), 8);
 let checksum = 0; for (let i=0;i<512;i++) checksum += i>=148 && i<156 ? 32 : bytes[i];
 if (stored !== checksum) throw Error('Повреждён заголовок пакета. Скачайте файл заново.');
 const prefix = decode(bytes.subarray(345,500));
 const path = (prefix ? prefix+'/' : '') + decode(bytes.subarray(0,100));
 const sizeText = decode(bytes.subarray(124,136));
 if (!/^[0-7]+$/.test(sizeText) || ![0,48].includes(bytes[156])) throw Error('Неподдерживаемый формат пакета.');
 return {path,size:parseInt(sizeText,8)};
}
async function importFiles(files, progress = () => {}) {
 const data = await manifest(), allowed = new Map(data.files.map(f => [f.path,f]));
 const total = Array.from(files).reduce((n,f)=>n+f.size,0); let done=0;
 if (!total) throw Error('Выберите скачанные файлы .tar.');
 await navigator.storage?.persist?.();
 for (const file of files) {
  let offset=0;
  while (offset+512 <= file.size) {
   const header = headerInfo(new Uint8Array(await file.slice(offset,offset+512).arrayBuffer()));
   if (!header) break;
   const item = allowed.get(header.path);
   if (!item || item.size !== header.size) throw Error('В пакете найден неизвестный файл: '+header.path);
   const end=offset+512+item.size;
   if(end>file.size)throw Error('Пакет скачан не полностью: '+file.name);
   if (!await present(item)) {
    const blob=file.slice(offset+512,end), bytes=await blob.arrayBuffer();
    const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');
    if(digest!==item.sha256)throw Error('Файл повреждён: '+item.path+'. Скачайте этот пакет повторно.');
    const cache=await caches.open(item.cache);
    await cache.put(target(item),new Response(blob,{headers:{'Content-Type':item.path.endsWith('.json')?'application/json':'application/octet-stream','x-tutor-sha256':digest}}));
   }
   const next=Math.ceil(end/512)*512;done+=next-offset;offset=next;
   progress('Сохраняю помощника · '+Math.min(100,Math.round(done/total*100))+'%');
  }
 }
 const groups=[];for(const group of new Set(data.files.map(f=>f.group)))if(await ready(group))groups.push(group);
 window.dispatchEvent(new CustomEvent('tutor-model-imported',{detail:groups}));
 return groups;
}
const setups=new WeakMap();
function cancel(){
 if(window.TutorNative)return window.TutorNative.invoke('cancel_model');
 downloadController?.abort();
}
async function mount(container, group, onReady, start=false) {
 if(group!=='qwen7b'){
  if(window.TutorSpeech)return window.TutorSpeech.showSetup(start);
  throw Error('Откройте настройки и установите голосовой ввод LocalSpeech.');
 }
 const existing=setups.get(container);if(existing?.running){container.hidden=false;return;}
 container.replaceChildren();container.hidden=false;
 const state={running:false};setups.set(container,state);
 const text=document.createElement('p');text.textContent='Qwen 7B · около 4,3 ГБ. Скачивание и настройка выполняются автоматически. Встроенный консультант работает и без этой модели.';
 const button=document.createElement('button');button.type='button';button.className='btn btn-primary';button.textContent='Скачать Qwen 7B';
 const stop=document.createElement('button');stop.type='button';stop.className='btn btn-default';stop.textContent='Отменить';stop.hidden=true;
 const bar=document.createElement('progress');bar.max=100;bar.hidden=true;bar.style.width='100%';bar.setAttribute('aria-label','Скачивание Qwen 7B');
 const status=document.createElement('p');status.setAttribute('role','status');status.setAttribute('aria-live','polite');
 const progress=value=>{status.textContent=String(value);const match=String(value).match(/(\d+)%/);if(match)bar.value=Number(match[1]);else bar.removeAttribute('value');};
 button.onclick=async()=>{
  if(state.running)return;state.running=true;button.disabled=true;stop.hidden=false;bar.hidden=false;bar.removeAttribute('value');status.textContent='Подключение…';
  try{await ensure(group,progress);bar.value=100;status.textContent='Qwen 7B установлен. Его можно выбрать в настройках помощника.';button.textContent='Проверить установленную модель';if(onReady)await onReady();}
  catch(error){status.textContent=error.name==='AbortError'?'Скачивание отменено. Проверенные файлы сохранены.':error.name==='QuotaExceededError'?'Недостаточно места. Освободите место и нажмите «Продолжить скачивание».':String(error.message||error);button.textContent='Продолжить скачивание';}
  finally{state.running=false;button.disabled=false;stop.hidden=true;bar.hidden=true;}
 };
 stop.onclick=()=>{stop.disabled=true;status.textContent='Отмена скачивания…';Promise.resolve(cancel()).catch(e=>status.textContent=String(e.message||e)).finally(()=>stop.disabled=false);};
 container.append(text,button,stop,bar,status);
 if(start)await button.onclick();
}
document.querySelectorAll('[data-model-group]').forEach(button=>button.addEventListener('click',()=>mount(document.getElementById('pwa-model-setup'),button.dataset.modelGroup,null,true).catch(error=>{document.getElementById('pwa-model-setup').textContent=error.message;})));
function selectBuiltIn(group){
 const id=group==='qwen7b'?'Qwen2.5-Coder-7B-Instruct-q4f16_1-MLC':group==='opencode'?'opencode-local':null;
 try{if(id&&localStorage.getItem('tutor-ai-model')===id)localStorage.setItem('tutor-ai-model','guided');}catch(_){}
}
// Component deletion is separate from learner-data reset and course offline caches.
async function remove(group) {
 if(!['qwen7b','whisper-tiny','localspeech','opencode'].includes(group))throw Error('Неизвестный компонент.');
 if(downloadController)throw Error('Сначала дождитесь завершения или отмените скачивание.');
 if(group==='opencode'){
  if(!window.TutorNative)throw Error('OpenCode удаляется в приложении PythonTutor.');
  await window.TutorNative.invoke('remove_cli');selectBuiltIn(group);return;
 }
 if(group==='qwen7b'){
  await window.TutorLocalAI?.unload?.();
  if(window.TutorNative)await window.TutorNative.invoke('remove_model');
 }
 if(group==='localspeech'){await window.TutorSpeech?.dispose?.();if(window.TutorNative)await window.TutorNative.invoke('remove_speech');}
 const originRoot=new URL('../../',base);
 const prefixes=group==='localspeech'?[new URL('static/local-speech/',originRoot).href]:[new URL(group+'/',base).href];
 const names=group==='qwen7b'?['webllm/model','webllm/config','webllm/wasm']:group==='whisper-tiny'?['transformers-cache']:['local-speech-verified-v1','tutor-local-speech-runtime-v1'];
 let removed=0;
 for(const name of await caches.keys()){
  if(!names.includes(name))continue;
  const cache=await caches.open(name);
  for(const request of await cache.keys()){
   if(prefixes.some(prefix=>request.url.startsWith(prefix))||(group==='localspeech'&&request.url===new URL('local-speech-manifest.json',document.currentScript?.src||manifestURL).href)){if(await cache.delete(request))removed++;}
  }
 }
 installedPromise=null;selectBuiltIn(group);
 window.dispatchEvent(new CustomEvent('tutor-component-removed',{detail:group}));
 return removed;
}
const deletePanel=document.getElementById('component-delete-options');
if(deletePanel){
 if(window.TutorNative)deletePanel.querySelector('[data-native-component]').hidden=false;
 document.getElementById('component-delete').addEventListener('click',async()=>{
  const selected=[...deletePanel.querySelectorAll('input:checked')].map(input=>input.value);
  const status=document.getElementById('component-delete-status');
  if(!selected.length){status.textContent='Выберите, что удалить.';return;}
  const button=document.getElementById('component-delete');button.disabled=true;
  try{for(const group of selected)await remove(group);status.textContent='Скачанные компоненты удалены. Прогресс, код и переписка сохранены.';deletePanel.querySelectorAll('input').forEach(input=>input.checked=false);}
  catch(e){status.textContent=String(e.message||e);}
  finally{button.disabled=false;}
 });
}
window.TutorModelAssets={cancel,ready,ensure,importFiles,mount,remove,base:base.href,headerInfo};
})();
