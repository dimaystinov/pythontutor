(function(){
'use strict';
const invoke=window.__TAURI__.core.invoke,$=id=>document.getElementById(id);let mode='login',legacyProfile=null;
function show(next){
 mode=next;const legacy=mode==='legacy',converting=mode==='convert';
 for(const [id,enabled] of [['student-fields',!legacy],['legacy-fields',legacy]]){$(id).hidden=!enabled;$(id).disabled=!enabled;}
 $('submit').textContent=converting?'Сохранить и войти':'Войти';
 $('student-title').textContent=converting?'Новые данные входа · прогресс сохранится':'Данные ученика';
 $('legacy-mode').hidden=converting;$('status').textContent='';$('pin').value='';
}
$('legacy-mode').onclick=()=>show(mode==='legacy'?'login':'legacy');
for(const id of ['surname','given-name'])$(id).addEventListener('input',()=>{const el=$(id),v=el.value.toLowerCase();if(el.value!==v){const pos=el.selectionStart;el.value=v;el.setSelectionRange(pos,pos);}});
for(const id of ['surname','given-name'])$(id).addEventListener('blur',()=>{$(id).value=$(id).value.trim().replace(/\s+/g,' ').toLowerCase();});
$('account').onsubmit=async event=>{
 event.preventDefault();$('submit').disabled=true;$('status').textContent='';
 try{
  if(mode==='legacy'){
   legacyProfile=await invoke('login',{name:$('legacy-name').value,password:$('legacy-password').value});
   $('legacy-password').value='';show('convert');$('surname').focus();return;
  }
  if(!/^(?:[1-9]|1[01])$/.test($('school-class').value))throw Error('Введите класс числом от 1 до 11, без буквы.');
  const args={surname:$('surname').value.trim().toLowerCase(),givenName:$('given-name').value.trim().toLowerCase(),schoolClass:Number($('school-class').value),password:$('pin').value,oldPin:$('old-pin').value||null};
  if([...args.password].length<8)throw Error('Пароль должен содержать не меньше 8 символов.');
  if(!Number.isInteger(args.schoolClass)||args.schoolClass<1||args.schoolClass>11)throw Error('Укажите класс числом от 1 до 11.');
  if(mode==='convert')args.legacy=legacyProfile.id;
  const profile=await invoke('enter_course',args);
  sessionStorage.setItem('tutor-native-profile',JSON.stringify(profile));sessionStorage.setItem('tutor-last-activity:'+profile.id,String(Date.now()));
  try{await invoke('autostart',{enabled:$('autostart').checked});}catch(e){console.warn('Autostart unavailable');}
  location.href='/pythontutor/';
 }catch(e){$('status').textContent=e.message||String(e);}finally{$('submit').disabled=false;}
};
})();
