/* Browser download: verified files go directly to their final inference cache.
 * The known ZIP_STORED distribution is streamed one file at a time; no ZIP copy. */
const SERVER='https://dimaystinov.duckdns.org/models/Qwen2.5-Coder-7B-Instruct-q4f16_1-MLC/';
const YANDEX='https://dimaystinov.duckdns.org/model-download/qwen-yandex.zip';
export async function checkedBytes(bytes,item){
 if(bytes.byteLength!==item.size)throw Error('Неверный размер: '+item.path);
 const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');
 if(hash!==item.sha256)throw Error('Контрольная сумма не совпала: '+item.path);
 return bytes;
}
async function next(reader,signal){
 signal?.throwIfAborted();let timer;
 try{return await Promise.race([reader.read(),new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('Источник не передаёт данные.')),30000);})]);}
 finally{clearTimeout(timer);}
}
async function stream(url,signal){
 const c=new AbortController(),stop=()=>c.abort(signal.reason);signal.addEventListener('abort',stop,{once:true});
 const timer=setTimeout(()=>c.abort(Error('Источник не отвечает.')),30000);
 try{const r=await fetch(url,{credentials:'omit',cache:'no-store',signal:c.signal});clearTimeout(timer);if(!r.ok)throw Error('HTTP '+r.status);return {response:r,close:()=>{clearTimeout(timer);signal.removeEventListener('abort',stop);c.abort();}};}
 catch(e){clearTimeout(timer);signal.removeEventListener('abort',stop);throw e;}
}
export async function readStoredZip(reader,files,save,signal,progress=()=>{}){
 let received=0;const total=files.reduce((n,f)=>n+f.size,0);
 const allowed=new Map(files.map(f=>[f.path,f]));let buffer=new Uint8Array(),offset=0;
 async function read(size){
  const result=new Uint8Array(size);let written=0;
  while(written<size){signal?.throwIfAborted();if(offset===buffer.length){const chunk=await next(reader,signal);if(chunk.done)throw Error('Архив скачан не полностью.');buffer=chunk.value;offset=0;received+=buffer.length;progress('Скачивание модели · '+Math.min(99,Math.floor(received/total*100))+'% · '+(received/1048576).toFixed(1)+' МБ');}
   const take=Math.min(size-written,buffer.length-offset);result.set(buffer.subarray(offset,offset+take),written);offset+=take;written+=take;}
  return result;
 }
 const seen=new Set();
 while(seen.size<allowed.size){
  const header=await read(30),v=new DataView(header.buffer);
  if(v.getUint32(0,true)!==0x04034b50)throw Error('В архиве отсутствуют файлы модели.');
  const flags=v.getUint16(6,true),method=v.getUint16(8,true),size=v.getUint32(18,true),unpacked=v.getUint32(22,true);
  if((flags&9)||method!==0||size!==unpacked)throw Error('Неподдерживаемый формат архива модели.');
  const name=new TextDecoder().decode(await read(v.getUint16(26,true)));await read(v.getUint16(28,true));
  const item=allowed.get(name);
  if(!item||item.size!==size||seen.has(name))throw Error('Неизвестный или повторный файл в архиве: '+name);
  await save(item,await read(size));seen.add(name);
 }
}
export async function downloadModel(files,{present,save,progress=()=>{},signal}){
 await navigator.storage?.persist?.();
 let missing=[];for(const item of files)if(!await present(item))missing.push(item);
 if(!missing.length)return;
 // A partially installed model resumes per-file, without downloading a ZIP again.
 if(missing.length===files.length){
  let transfer;
  try{
   progress('Подключаю Яндекс Диск…');
   transfer=await stream(YANDEX,signal);let count=0;
   await readStoredZip(transfer.response.body.getReader(),files,async(item,bytes)=>{await save(item,await checkedBytes(bytes,item));progress('Сохраняю модель с Яндекс Диска · '+(++count)+'/'+files.length);},signal,progress);
   progress('Модель сохранена. 100%');return;
  }catch(e){signal.throwIfAborted();if(e.name==='QuotaExceededError')throw e;progress('Яндекс Диск недоступен из браузера. Подключаю резервные источники…');}
  finally{transfer?.close();}
 }
 let count=0;
 for(const item of files){
  signal.throwIfAborted();if(await present(item)){count++;continue;}
  const name=item.path.slice('qwen7b/'.length);let done=false;
  for(const [label,url] of [['Сервер',SERVER+name],['Hugging Face / MLC',item.source]]){
   let transfer;
   try{
    if(!url)throw Error('Не указан резервный адрес.');progress(label+' · файл '+(count+1)+'/'+files.length);
    transfer=await stream(url,signal);const reader=transfer.response.body.getReader(),bytes=new Uint8Array(item.size);let offset=0;
    for(;;){const part=await next(reader,signal);if(part.done)break;if(offset+part.value.length>bytes.length)throw Error('Неверный размер файла.');bytes.set(part.value,offset);offset+=part.value.length;progress(label+' · файл '+(count+1)+'/'+files.length+' · '+Math.min(99,Math.floor(offset/item.size*100))+'% · '+(offset/1048576).toFixed(1)+' из '+(item.size/1048576).toFixed(1)+' МБ');}
    if(offset!==item.size)throw Error('Файл скачан не полностью.');
    await save(item,await checkedBytes(bytes,item));done=true;break;
   }catch(e){signal.throwIfAborted();if(e.name==='QuotaExceededError')throw e;}
   finally{transfer?.close();}
  }
  if(!done)throw Error('Не удалось скачать '+name+'. Проверьте сеть и повторите: проверенные файлы сохранены.');
  count++;
 }
 progress('Модель сохранена в браузере. Повторная загрузка не нужна.');
}
