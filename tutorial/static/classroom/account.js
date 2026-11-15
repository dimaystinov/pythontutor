(() => {
'use strict';
if (window.__TAURI__) return;
const sessionKey='pt-student-v1', activityKey='pt-student-activity', encoder=new TextEncoder();
const endpoint='https://109-196-164-69.sslip.io/progress';
const base=new URL('./',document.currentScript.src);
const hex=bytes=>Array.from(new Uint8Array(bytes),b=>b.toString(16).padStart(2,'0')).join('');
const sha=async value=>hex(await crypto.subtle.digest('SHA-256',typeof value==='string'?encoder.encode(value):value));
function normalize(name){
 const en="qwertyuiop[]asdfghjkl;'zxcvbnm,.`",ru='йцукенгшщзхъфывапролджэячсмитьбюё';
 const v=Array.from(name.trim().toLowerCase(),c=>en.includes(c)?ru[en.indexOf(c)]:c).join('').replace(/ё/g,'е').replace(/\s+/g,' ');
 if(!/^[а-я -]{1,40}$/.test(v)||!/[а-я]/.test(v))throw Error('Проверьте имя и фамилию.');
 return v;
}
async function identity(surname,given,grade){
 if(!/^(?:[1-9]|1[01])$/.test(grade))throw Error('Класс — число от 1 до 11.');
 return sha('PythonTutor:student:v1:'+normalize(surname)+'|'+normalize(given)+'|'+grade);
}
function session(){
 if(Date.now()-Number(sessionStorage.getItem(activityKey))>=600000){sessionStorage.removeItem(sessionKey);return null;}
 return JSON.parse(sessionStorage.getItem(sessionKey)||'null');
}
const profile=session();
const meta=document.querySelector('meta[name=learner-id]');
if(profile&&meta)meta.content=profile.id;
const valid=()=>profile?.id===session()?.id;
if(profile){
 const touch=()=>{if(!valid()){location.reload();return;}sessionStorage.setItem(activityKey,Date.now());};
 for(const event of ['pointerdown','keydown','wheel','touchstart'])window.addEventListener(event,touch,{passive:true});
 setInterval(()=>{if(!valid())location.reload();},10000);
}
async function post(data){
 const r=await fetch(endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data),credentials:'omit',signal:AbortSignal.timeout(8000)});
 if(!r.ok)throw Error(r.status===403?'Неверный пароль.':'Сервер ответил '+r.status);
 return r.json();
}
function loadArgon(){return new Promise((resolve,reject)=>{if(window.hashwasm)return resolve();const s=document.createElement('script');s.src=new URL('vendor/argon2.umd.min.js',base);s.onload=resolve;s.onerror=()=>reject(Error('Для первого входа офлайн сначала скачайте курс.'));document.head.append(s);});}
async function login(f){
 const id=await identity(f.surname.value,f.given.value,f.grade.value),pw=f.password.value;
 if([...pw].length<8||encoder.encode(pw).length>256)throw Error('Пароль — от 8 символов, до 256 байт.');
 await loadArgon();
 const proof=await sha(await hashwasm.argon2id({password:pw,salt:id,parallelism:1,iterations:2,memorySize:19456,hashLength:32,outputType:'binary'}));
 const verifier=await sha(proof),known=localStorage.getItem('pt-verifier:'+id);
 if(known&&known!==verifier)throw Error('Неверный пароль.');
 try{await post({op:'login',id,proof});}catch(e){if(!(e instanceof TypeError)&&!['TimeoutError','AbortError'].includes(e.name))throw e;}
 localStorage.setItem('pt-verifier:'+id,verifier);
 sessionStorage.setItem(activityKey,Date.now());sessionStorage.setItem(sessionKey,JSON.stringify({id,proof,name:normalize(f.given.value)+' '+normalize(f.surname.value)}));location.reload();
}
let pending=false,busy=false;
async function sync(){
 if(!profile||!valid()||!window.TutorDevice)return;
 if(busy){pending=true;return;}busy=true;
 const note=document.getElementById('class-status');
 try{
 const auth={id:profile.id,proof:profile.proof},state=await TutorDevice.syncSnapshot(),remote=await post({...auth,op:'login'});
 const epoch=state.epoch??remote.epoch;
 const items=state.items.map(({kind,slug,time,solved,code,acceptedCode})=>({kind,slug,time,solved,code,acceptedCode:acceptedCode||''}));
 const reply=await post({...auth,op:'sync',epoch,reset:state.epoch!=null&&!!state.reset,items});
 if(!valid())return;
 await TutorDevice.applySync(state,reply,epoch);
 window.dispatchEvent(new Event('tutor-sync-finished'));if(note)note.textContent='Прогресс синхронизирован.';
 }catch(e){if(note)note.textContent='Решения сохранены в браузере. '+(e instanceof TypeError?'Нет связи с сервером.':e.message);}
 finally{busy=false;if(pending){pending=false;sync();}}
}
window.PTClass={identity,post,valid};
document.addEventListener('DOMContentLoaded',()=>{
 const host=document.getElementById('class-account');
 if(host){host.hidden=false;
 host.querySelector('form').hidden=!!profile;
 const logout=host.querySelector('[data-logout]');logout.hidden=!profile;
 if(profile)host.querySelector('[data-name]').textContent=profile.name;
 logout.onclick=()=>{sessionStorage.removeItem(sessionKey);location.reload();};
 const form=host.querySelector('form');
 for(const field of [form.surname,form.given])field.oninput=()=>{field.value=field.value.toLowerCase();};
 form.onsubmit=async e=>{e.preventDefault();const button=form.querySelector('button');button.disabled=true;try{await login(form);}catch(err){document.getElementById('class-status').textContent=err.message;}finally{button.disabled=false;}};
 }
 if(profile){window.addEventListener('online',sync);window.addEventListener('tutor-progress-changed',sync);setInterval(sync,60000);sync();}
});
})();
