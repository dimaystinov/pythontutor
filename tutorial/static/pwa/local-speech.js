/* Optional LocalSpeech 0.3.0. All executable assets and weights are installed by a user action. */
(function(){
'use strict';
const script=new URL(document.currentScript.src),base=new URL('../local-speech/0.3.0/',script),manifestURL=new URL('local-speech-manifest.json',script);
const runtime='tutor-local-speech-runtime-v1',weights='local-speech-verified-v1';
let client,installing=false,aborter,active=false;
async function manifest(){const cache=await caches.open(runtime),saved=await cache.match(manifestURL);if(saved)return saved.json();const r=await fetch(manifestURL);if(!r.ok)throw Error('Не найден список файлов LocalSpeech.');await cache.put(manifestURL,r.clone());return r.json();}
function key(file){const url=new URL(file.path,base);if(file.path.startsWith('models/')&&!file.path.endsWith('/LICENSE'))url.searchParams.set('sha256',file.sha256);return url.href;}
function cacheName(file){return file.path.startsWith('models/')||file.path==='evidence/model-manifest.json'?weights:runtime;}
async function ready(){
 if(window.TutorNative)return window.TutorNative.invoke('speech_status');
 const m=await manifest();for(const file of m.files){const r=await (await caches.open(cacheName(file))).match(key(file));if(r?.headers.get('x-tutor-sha256')!==file.sha256)return false;}return true;
}
async function install(progress=()=>{}){
 if(installing)throw Error('LocalSpeech уже скачивается.');installing=true;
 try{
  if(window.TutorNative){const off=await window.__TAURI__.event.listen('speech-progress',({payload})=>progress(payload));try{await window.TutorNative.invoke('install_speech');}finally{off();}return;}
  if(!navigator.serviceWorker?.controller)throw Error('Перезагрузите страницу, чтобы включить хранение голосового компонента.');
  aborter=new AbortController();const m=await manifest(),total=m.files.reduce((n,f)=>n+f.bytes,0);let done=0;
  for(const file of m.files){
   const cache=await caches.open(cacheName(file)),saved=await cache.match(key(file));
   if(saved?.headers.get('x-tutor-sha256')===file.sha256){done+=file.bytes;progress(Math.round(done/total*100));continue;}
   const r=await fetch(new URL(file.path,base),{signal:aborter.signal});if(!r.ok)throw Error('Не удалось скачать LocalSpeech: '+file.path);
   const bytes=await r.arrayBuffer(),hash=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(n=>n.toString(16).padStart(2,'0')).join('');
   if(bytes.byteLength!==file.bytes||hash!==file.sha256)throw Error('Файл LocalSpeech повреждён. Повторите загрузку.');
   const type=/\.m?js$/.test(file.path)?'text/javascript':file.path.endsWith('.wasm')?'application/wasm':file.path.endsWith('.json')?'application/json':'application/octet-stream';
   await cache.put(key(file),new Response(bytes,{headers:{'content-type':type,'x-tutor-sha256':hash}}));done+=file.bytes;progress(Math.round(done/total*100));
  }
 }finally{installing=false;aborter=null;}
}
function cancel(){aborter?.abort();if(window.TutorNative)window.TutorNative.invoke('cancel_speech');}
async function prepare(){if(!await ready()){showSetup();throw Error('Сначала скачайте голосовой ввод кнопкой «Установить LocalSpeech».');}}
async function dispose(){if(installing)throw Error('Сначала завершите или отмените скачивание LocalSpeech.');if(active)throw Error('Сначала завершите распознавание речи.');if(client){await client.dispose();client=null;}}
async function transcribe(chunks,_rate,progress){
 await prepare();if(active)throw Error('Дождитесь распознавания речи.');active=true;
 try{
  progress?.('Распознаю речь…');const sdk=await import(new URL('local-speech.mjs',base));
  client=sdk.create({assetBaseURL:base.href,language:'ru',allowLargeModels:false,cacheOnly:!window.TutorNative,terms:['Python','переменная','цикл','условие']});
  const finals=new Map();let failure;
  client.on('final',event=>finals.set(event.sessionId+':'+event.segmentId,event.rawText||''));client.on('error',event=>{failure=event.message;});
  await client.start({input:'pcm'});
  // Existing capture resamples audio to 16 kHz. Feed <=1s packets with backpressure.
  for(const chunk of chunks){for(let i=0;i<chunk.length;i+=16000){const samples=Float32Array.from(chunk.subarray(i,i+16000),n=>n/32768);await client.write(samples,16000);}}
  await client.stop();if(failure)throw Error(failure);const text=[...finals.values()].join(' ').trim();if(!text)throw Error('Речь не распознана. Повторите или напишите вопрос.');return text;
 }finally{active=false;if(client){await client.dispose();client=null;}}
}
function showSetup(){
 let box=document.getElementById('localspeech-setup');if(!box){box=document.createElement('section');box.id='localspeech-setup';box.style.cssText='padding:16px;margin:12px;background:#eef7ff;border-radius:10px';
 box.innerHTML='<p>Голосовой ввод LocalSpeech · русский язык · 43 МБ</p><button type="button" class="btn btn-default">Установить LocalSpeech</button> <button type="button" hidden>Отменить</button><progress hidden max="100" style="width:100%"></progress><p role="status"></p>';
 const host=document.getElementById('tutor-messages')||document.getElementById('pwa-model-setup');host.before(box);
 const [button,stop]=box.querySelectorAll('button'),bar=box.querySelector('progress'),note=box.querySelector('[role=status]');
 button.onclick=async()=>{button.disabled=true;stop.hidden=false;bar.hidden=false;bar.value=0;note.textContent='Подключение…';try{await install(n=>{bar.value=n;note.textContent='Скачивание · '+n+'%';});note.textContent='Готово. Нажмите микрофон для диктовки.';}catch(e){note.textContent=e.name==='AbortError'?'Скачивание отменено.':String(e.message||e);}finally{button.disabled=false;stop.hidden=true;bar.hidden=true;}};
 stop.onclick=cancel;
 }box.hidden=false;return box;
}
window.TutorSpeech={prepare,transcribe,dispose,install,ready,cancel,showSetup};
document.querySelectorAll('[data-speech-install]').forEach(button=>button.addEventListener('click',showSetup));
})();
