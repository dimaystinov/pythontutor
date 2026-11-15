'use strict';
const encoder=new TextEncoder();
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

async function post(data){
 const response=await fetch('/journal',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data),cache:'no-store'});
 if(!response.ok)throw Error(response.status===403?'Неверный пароль.':'Ошибка журнала: '+response.status);
 return response.json();
}
window.PTClass={identity,post};
