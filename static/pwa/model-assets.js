/* Import verified release packages directly into the inference libraries' caches. */
(function () {
'use strict';
const base = new URL('../models/', document.currentScript.src);
const manifestURL = new URL('model-assets.json', document.currentScript.src);
let manifestPromise,installedPromise;
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
async function ensure(group) {
 if (await ready(group)) return;
 window.dispatchEvent(new CustomEvent('tutor-model-needed', {detail: group}));
 throw Error('Подготовьте помощника один раз: скачайте пакеты и выберите их ниже.');
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
async function mount(container, group, onReady) {
 const data=await manifest();container.replaceChildren();container.hidden=false;
 const text=document.createElement('p');text.textContent='Установщик скачает все части, проверит их и настроит помощника. Для офлайн-ИИ отметьте Qwen 7B при установке. Ручная загрузка также доступна ниже. ';/*group==='qwen7b'?'Один раз скачайте 3 пакета (4,3 ГБ), затем выберите их вместе. Дальше помощник запускается сам, без интернета.':'Один раз скачайте пакет голосового ввода (около 46 МБ) и выберите его здесь.';*/
 const links=document.createElement('div');
 for(const pack of data.packages.filter(p=>p.group===group)){
  const link=document.createElement('a');link.href='https://github.com/dimaystinov/pythontutor/releases/download/'+data.release+'/'+pack.name;link.textContent=pack.name;link.download=pack.name;link.style.display='block';links.append(link);
 }
 const download=document.createElement('a');download.className='btn btn-primary';download.textContent='Установить автоматически';download.href='https://github.com/dimaystinov/pythontutor/releases/tag/desktop-v1.2.2';download.target='_blank';download.rel='noopener noreferrer';
 const details=document.createElement('details'),summary=document.createElement('summary');summary.textContent='Ссылки на отдельные пакеты';details.append(summary,links);
 const label=document.createElement('label');label.textContent='Выбрать скачанные пакеты';label.className='btn btn-default';
 const input=document.createElement('input');input.type='file';input.multiple=true;input.accept='.tar';input.style.display='block';input.setAttribute('aria-label','Пакеты локального помощника');label.append(input);
 const status=document.createElement('p');status.setAttribute('role','status');
 input.onchange=async()=>{input.disabled=true;try{const groups=await importFiles(input.files,t=>status.textContent=t);if(groups.includes(group)){status.textContent=onReady?'Готово! Запускаю…':'Готово. Помощник подготовлен для работы без интернета.';if(onReady){await onReady();container.hidden=true;}}else status.textContent='Файлы сохранены. Выберите оставшиеся пакеты.';}catch(error){status.textContent=error.name==='QuotaExceededError'?'Недостаточно места на устройстве. Освободите место и повторите выбор пакетов.':error.message;}finally{input.disabled=false;input.value='';}};
 container.append(text,download,details,label,status);
}
document.querySelectorAll('[data-model-group]').forEach(button=>button.addEventListener('click',()=>mount(document.getElementById('pwa-model-setup'),button.dataset.modelGroup).catch(error=>{document.getElementById('pwa-model-setup').textContent=error.message;})));
window.TutorModelAssets={ready,ensure,importFiles,mount,base:base.href,headerInfo};
})();
