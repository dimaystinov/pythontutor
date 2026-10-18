/* Only public snapshots and allowlisted course assets are cached, never user HTML/API. */
const META='tutor-pwa-meta-v1', POINTER='/__pwa_ready', MODE='/__pwa_local';
self.addEventListener('install',event=>event.waitUntil(self.skipWaiting()));
self.addEventListener('activate',event=>event.waitUntil(self.clients.claim()));
async function configuration(){const c=await caches.open(META),r=await c.match(POINTER);return r?await r.json():null;}
async function localMode(){return !!(await (await caches.open(META)).match(MODE));}
let downloading=false;
self.addEventListener('message',event=>{
 const port=event.ports[0],send=data=>port?.postMessage(data);
 event.waitUntil((async()=>{
  if(event.data.type==='status'){send({ready:await configuration(),local:await localMode()});return;}
  if(event.data.type==='mode'){
   const c=await caches.open(META); if(event.data.local)await c.put(MODE,new Response('1'));else await c.delete(MODE);
   send({ok:true});return;
  }
  if(event.data.type!=='download')return;
  if(downloading){send({error:'Загрузка уже выполняется в другой вкладке.'});return;}
  downloading=true;const name='tutor-pwa-pack-'+Date.now();
  try{
   const response=await fetch('/pwa/download-manifest/',{cache:'no-store',credentials:'omit'});
   if(!response.ok)throw Error('Не удалось получить список файлов курса.');
   const manifest=await response.json(),cache=await caches.open(name);
   const tasks=[...manifest.resources.map(url=>({key:url,url})),...manifest.pages.map(path=>({key:path,url:'/pwa/page/?path='+encodeURIComponent(path)}))];
   let done=0,cursor=0,bytes=0;
   async function load(){while(cursor<tasks.length){const task=tasks[cursor++];
    const r=await fetch(task.url,{cache:'reload',credentials:'omit'});
    if(!r.ok||r.redirected)throw Error('Не удалось скачать '+task.key);
    if(r.body){const reader=r.body.getReader();const body=new ReadableStream({async pull(controller){try{const chunk=await reader.read();if(chunk.done){controller.close();return;}bytes+=chunk.value.byteLength;send({done,total:tasks.length,bytes});controller.enqueue(chunk.value);}catch(e){controller.error(e);}},cancel(reason){return reader.cancel(reason);}});await cache.put(task.key,new Response(body,{status:r.status,statusText:r.statusText,headers:r.headers}));}else await cache.put(task.key,r);
    done++;send({done,total:tasks.length,bytes});
   }}
   const results=await Promise.allSettled(Array.from({length:4},load));
   const failure=results.find(r=>r.status==='rejected');if(failure)throw failure.reason;
   const meta=await caches.open(META),previous=await configuration();
   const ready={name,version:manifest.version,files:tasks.length,date:new Date().toISOString()};
   await meta.put(POINTER,new Response(JSON.stringify(ready)));
   if(previous?.name!==name && previous?.name)await caches.delete(previous.name);
   send({ready});
  }catch(error){await caches.delete(name);send({error:String(error.message||error)});}
  finally{downloading=false;}
 })());
});
self.addEventListener('fetch',event=>{
 const req=event.request,url=new URL(req.url);
 if(req.method!=='GET'||url.origin!==self.location.origin)return;
 event.respondWith((async()=>{
  if(url.pathname.endsWith('/local-speech-catalog.json')){try{return await fetch(req,{cache:'no-store'});}catch(_){return new Response(JSON.stringify({schemaVersion:1,versions:[]}),{headers:{'content-type':'application/json'}});}}
  if(/\/static\/local-speech\/\d+\.\d+\.\d+\//.test(url.pathname)){
   for(const name of ['tutor-local-speech-runtime-v1','local-speech-verified-v1']){
    const saved=await (await caches.open(name)).match(req,{ignoreSearch:true});if(saved)return saved;
   }
   return fetch(req);
  }
  const config=await configuration(),cache=config?await caches.open(config.name):null;
  const saved=cache?await cache.match(url.pathname):null;
  if(saved && await localMode())return saved;
  try{const response=await fetch(req);if(response.status>=500&&saved)return saved;return response;}
  catch(error){if(saved)return saved;
   if(req.mode==='navigate')return new Response('<meta charset="utf-8"><h1>Эта страница требует сети</h1><p>Учётная запись, преподаватель и ИИ доступны на сайте.</p><a href="/">К скачанным урокам</a> · <a href="/pwa/">Офлайн-приложение</a>',{status:503,headers:{'Content-Type':'text/html; charset=utf-8'}});
   throw error;
  }
 })());
});
