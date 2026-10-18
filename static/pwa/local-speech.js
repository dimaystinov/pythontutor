/* Optional LocalSpeech 0.3.0. All executable assets and weights are installed by a user action. */
(function(){
'use strict';
const script=new URL(document.currentScript.src),manifestURL=new URL('local-speech-manifest.json',script);
const validVersion=v=>typeof v==='string'&&/^\d{1,7}\.\d{1,7}\.\d{1,7}$/.test(v);
const assetBase=v=>new URL('../local-speech/'+v+'/',script);
async function activeVersion(){if(window.TutorNative)return window.TutorNative.invoke('speech_active_version');try{const v=localStorage.getItem('tutor-speech-active-version');if(validVersion(v))return v;}catch(_){}return '0.3.0';}
async function activate(v){if(window.TutorNative)return window.TutorNative.invoke('activate_speech',{version:v});localStorage.setItem('tutor-speech-active-version',v);let versions=[];try{versions=JSON.parse(localStorage.getItem('tutor-speech-versions')||'[]');}catch(_){}localStorage.setItem('tutor-speech-versions',JSON.stringify([...new Set([...versions.filter(validVersion),v])]));}
const runtime='tutor-local-speech-runtime-v1',weights='local-speech-verified-v1';
let client,installing=false,aborter,active=false;
function validateManifest(m,v){
 if(!validVersion(v)||m.version!==v||(m.apiVersion||1)!==1||m.base!=='https://dimaystinov.github.io/pythontutor/static/local-speech/'+v+'/'||!Array.isArray(m.files)||m.files.length>200||!m.files.some(f=>f.path==='local-speech.mjs'))throw Error('Несовместимый пакет LocalSpeech.');
 const paths=new Set();let total=0;
 for(const f of m.files){if(!/^[a-zA-Z0-9_./-]+$/.test(f.path)||f.path.split('/').some(p=>!p||p==='.'||p==='..')||paths.has(f.path)||!Number.isSafeInteger(f.bytes)||f.bytes<=0||f.bytes>300000000||!/^([a-f0-9]{64})$/i.test(f.sha256))throw Error('Неверный список файлов LocalSpeech.');paths.add(f.path);total+=f.bytes;}
 if(total>500000000)throw Error('Пакет LocalSpeech слишком большой.');return m;
}
async function manifest(v='0.3.0'){
 if(!validVersion(v))throw Error('Неверная версия LocalSpeech.');
 const url=v==='0.3.0'?manifestURL:new URL('pythontutor-manifest.json',assetBase(v));
 const cache=await caches.open(runtime),saved=await cache.match(url);if(saved)return validateManifest(await saved.json(),v);
 const r=await fetch(url,{cache:'no-store'});if(!r.ok)throw Error('Не найден пакет LocalSpeech '+v+'.');const m=validateManifest(await r.clone().json(),v);await cache.put(url,r);return m;
}
function key(file,v='0.3.0'){const url=new URL(file.path,assetBase(v));if(file.path.startsWith('models/')&&!file.path.endsWith('/LICENSE'))url.searchParams.set('sha256',file.sha256);return url.href;}
async function catalog(){const r=await fetch(window.TutorNative?'https://dimaystinov.github.io/pythontutor/static/pwa/local-speech-catalog.json':new URL('local-speech-catalog.json',script),{cache:'no-store',signal:AbortSignal.timeout(8000)});if(!r.ok)throw Error('Не удалось проверить новые версии SDK.');const data=await r.json();if(data.schemaVersion!==1||!Array.isArray(data.versions))throw Error('Неверный каталог SDK.');return data.versions.filter(v=>validVersion(v.version)&&v.apiVersion===1).map(v=>v.version);}
function cacheName(file){return file.path.startsWith('models/')||file.path==='evidence/model-manifest.json'?weights:runtime;}
async function ready(v){
 v=v||await activeVersion();
 if(window.TutorNative)return (await window.TutorNative.invoke('speech_installed_versions')).includes(v);
 const m=await manifest(v);for(const file of m.files){const r=await (await caches.open(cacheName(file))).match(key(file,v));if(r?.headers.get('x-tutor-sha256')!==file.sha256)return false;}return true;
}
async function install(progress=()=>{},v='0.3.0'){
 if(!validVersion(v))throw Error('Неверная версия SDK.');await dispose();
 if(installing)throw Error('LocalSpeech уже скачивается.');installing=true;
 try{
  if(window.TutorNative){const off=await window.__TAURI__.event.listen('speech-progress',({payload})=>typeof payload==='number'?progress(payload):progress(payload.percent,payload));try{await window.TutorNative.invoke('install_speech',{version:v});}finally{off();}return;}
  if(!navigator.serviceWorker?.controller)throw Error('Перезагрузите страницу, чтобы включить хранение голосового компонента.');
  aborter=new AbortController();const m=await manifest(v),total=m.files.reduce((n,f)=>n+f.bytes,0);let done=0;
  const report=(received=0,phase='Скачивание')=>progress(Math.min(99,Math.floor((done+received)/total*100)),{loaded:done+received,total,phase});
  report();
  for(const file of m.files){
   const cache=await caches.open(cacheName(file)),saved=await cache.match(key(file,v));
   if(saved?.headers.get('x-tutor-sha256')===file.sha256){done+=file.bytes;report();continue;}
   const r=await fetch(new URL(file.path,assetBase(v)),{signal:aborter.signal,cache:'no-store'});if(!r.ok)throw Error('Не удалось скачать LocalSpeech: '+file.path);
   const parts=[];let received=0;
   if(r.body){const reader=r.body.getReader();try{while(true){const {done:end,value}=await reader.read();if(end)break;received+=value.byteLength;if(received>file.bytes)throw Error('Неверный размер файла LocalSpeech.');parts.push(value);report(received);}}finally{reader.releaseLock();}}
   else{const part=new Uint8Array(await r.arrayBuffer());parts.push(part);received=part.byteLength;report(received);}
   const bytes=new Uint8Array(received);let offset=0;for(const part of parts){bytes.set(part,offset);offset+=part.byteLength;}
   report(received,'Проверка файла');
   const hash=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(n=>n.toString(16).padStart(2,'0')).join('');
   if(bytes.byteLength!==file.bytes||hash!==file.sha256)throw Error('Файл LocalSpeech повреждён. Повторите загрузку.');
   const type=/\.m?js$/.test(file.path)?'text/javascript':file.path.endsWith('.wasm')?'application/wasm':file.path.endsWith('.json')?'application/json':'application/octet-stream';
   await cache.put(key(file,v),new Response(bytes,{headers:{'content-type':type,'x-tutor-sha256':hash}}));done+=file.bytes;report();
  }
  await activate(v);progress(100,{loaded:total,total,phase:'Готово'});
 }finally{installing=false;aborter=null;}
}
function cancel(){aborter?.abort();if(window.TutorNative)window.TutorNative.invoke('cancel_speech');}
async function prepare(){if(!await ready()){showSetup();throw Error('Сначала скачайте голосовой ввод кнопкой «Установить LocalSpeech».');}}
async function dispose(){if(installing)throw Error('Сначала завершите или отмените скачивание LocalSpeech.');if(active)throw Error('Сначала завершите распознавание речи.');if(client){await client.dispose();client=null;}}
async function transcribe(chunks,_rate,progress){
 await prepare();if(active)throw Error('Дождитесь распознавания речи.');active=true;
 try{
  progress?.('Распознаю речь…');const base=assetBase(await activeVersion()),sdk=await import(new URL('local-speech.mjs',base));
  return await window.TutorSpeechAdapter.transcribe(sdk,{assetBaseURL:base.href,language:'ru',maxSegmentSeconds:6,allowLargeModels:false,cacheOnly:!window.TutorNative,terms:['Питон','переменная','цикл','условие','функция','список']},chunks);
 }finally{active=false;if(client){await client.dispose();client=null;}}
}
function showSetup(start=false){
 let box=document.getElementById('localspeech-setup');if(!box){box=document.createElement('section');box.id='localspeech-setup';box.style.cssText='padding:16px;margin:12px;background:#eef7ff;border-radius:10px';
 box.innerHTML='<p>Голосовой ввод LocalSpeech · русский язык</p><p data-speech-version>Версия 0.3.0 · около 43 МБ</p><label>Версия SDK <select aria-label="Версия LocalSpeech"><option value="0.3.0">0.3.0</option></select></label> <button type="button" data-speech-refresh>Проверить версии</button><button type="button" class="btn btn-default">Установить LocalSpeech</button> <button type="button" hidden>Отменить</button><progress hidden max="100" style="width:100%"></progress><p role="status"></p>';
 const host=document.getElementById('pwa-model-setup')||document.getElementById('tutor-messages');host.before(box);
 const buttons=box.querySelectorAll('button'),[refresh,button,stop]=buttons,select=box.querySelector('select'),versionNote=box.querySelector('[data-speech-version]'),bar=box.querySelector('progress'),note=box.querySelector('[role=status]');
 button.onclick=async()=>{if(installing)return;const chosen=select.value;button.disabled=true;select.disabled=true;refresh.disabled=true;stop.hidden=false;bar.hidden=false;bar.value=0;note.textContent='Подключение…';try{await install((n,info)=>{bar.value=n;note.textContent=(info?.phase||'Скачивание')+' · '+n+'%'+(info?' · '+(info.loaded/1048576).toFixed(1)+' из '+(info.total/1048576).toFixed(1)+' МБ':'');},chosen);note.textContent='LocalSpeech '+chosen+' готов. Нажмите микрофон для диктовки.';versionNote.textContent='Используется версия '+chosen;}catch(e){note.textContent=e.name==='AbortError'?'Скачивание отменено.':String(e.message||e);}finally{button.disabled=false;select.disabled=false;refresh.disabled=false;stop.hidden=true;bar.hidden=true;}};
 stop.onclick=cancel;
 async function versions(remote=true){if(installing)return;refresh.disabled=true;button.disabled=true;select.disabled=true;try{
  const current=await activeVersion();let available=['0.3.0'],catalogError='';if(remote)try{available=await catalog();}catch(e){catalogError=e.message;}let installed=[];
  if(window.TutorNative)installed=await window.TutorNative.invoke('speech_installed_versions');else{let previous=[];try{previous=JSON.parse(localStorage.getItem('tutor-speech-versions')||'[]');}catch(_){}for(const v of new Set([...available,current,...previous.filter(validVersion)])){try{if(await ready(v))installed.push(v);}catch(_){}}}
  versionNote.textContent=installed.includes(current)?'Используется версия '+current:'Голосовой ввод не установлен';
  select.replaceChildren();for(const v of new Set([...available,...installed,current])){const option=document.createElement('option');option.value=v;option.textContent=v+(installed.includes(v)?' · установлена':'');select.append(option);}select.value=current;
  note.textContent=catalogError?catalogError+' Установленные версии доступны без интернета.':'Выберите версию. Ранее установленную можно включить снова без скачивания.';
 }catch(e){note.textContent=e.message;}finally{refresh.disabled=false;button.disabled=false;select.disabled=false;}}
 refresh.onclick=()=>versions(true);box.versionReady=versions(!start);

 }box.hidden=false;if(start&&!installing)Promise.resolve(box.versionReady).then(()=>box.querySelectorAll('button')[1].click());return box;
}
window.TutorSpeech={prepare,transcribe,dispose,install,ready,cancel,showSetup,activeVersion,catalog};
document.querySelectorAll('[data-speech-install]').forEach(button=>button.addEventListener('click',()=>showSetup(true)));
})();
