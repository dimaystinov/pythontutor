(function(){
'use strict';
const invoke=window.__TAURI__.core.invoke,$=id=>document.getElementById(id);let mode='login',legacyProfile=null;
function show(next){
 mode=next;const legacy=mode==='legacy',converting=mode==='convert';
 for(const [id,enabled] of [['student-fields',!legacy],['legacy-fields',legacy]]){$(id).hidden=!enabled;$(id).disabled=!enabled;}
 $('submit').textContent=converting?'Сохранить и войти':mode==='register'?'Создать профиль':'Войти';
 $('student-title').textContent=converting?'Новые данные входа · прогресс сохранится':'Данные ученика';
 for(const m of ['login','register']){$(m+'-mode').classList.toggle('selected',m===mode);$(m+'-mode').hidden=converting;}
 $('legacy-mode').hidden=converting;$('status').textContent='';$('pin').value='';
}
$('login-mode').onclick=()=>show('login');$('register-mode').onclick=()=>show('register');$('legacy-mode').onclick=()=>show(mode==='legacy'?'login':'legacy');
for(const id of ['surname','given-name'])$(id).addEventListener('blur',()=>{$(id).value=$(id).value.trim().replace(/\s+/g,' ').toLowerCase();});
$('account').onsubmit=async event=>{
 event.preventDefault();$('submit').disabled=true;$('status').textContent='';
 try{
  if(mode==='legacy'){
   legacyProfile=await invoke('login',{name:$('legacy-name').value,password:$('legacy-password').value});
   $('legacy-password').value='';show('convert');$('surname').focus();return;
  }
  const args={surname:$('surname').value,givenName:$('given-name').value,schoolClass:Number($('school-class').value),pin:$('pin').value};
  if(!/^\d{4}$/.test(args.pin))throw Error('PIN-код должен содержать ровно 4 цифры.');
  if(!Number.isInteger(args.schoolClass)||args.schoolClass<1||args.schoolClass>11)throw Error('Укажите класс числом от 1 до 11.');
  const command=mode==='convert'?'convert_student':mode==='register'?'register_student':'login_student';
  if(mode==='convert')args.profile=legacyProfile.id;
  const profile=await invoke(command,args);
  sessionStorage.setItem('tutor-native-profile',JSON.stringify(profile));sessionStorage.setItem('tutor-last-activity:'+profile.id,String(Date.now()));
  try{await invoke('autostart',{enabled:$('autostart').checked});}catch(e){console.warn('Autostart unavailable');}
  location.href='/pythontutor/';
 }catch(e){$('status').textContent=e.message||String(e);}finally{$('submit').disabled=false;}
};
})();
