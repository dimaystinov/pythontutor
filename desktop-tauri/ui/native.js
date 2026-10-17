(function(){
'use strict';
if(!window.__TAURI__)return;
const invoke=window.__TAURI__.core.invoke;let profile;try{profile=JSON.parse(sessionStorage.getItem('tutor-native-profile'));}catch(_){}
if(!profile?.id){location.replace('/index.html');return;}
window.TutorNative={profile,invoke:(name,args={})=>invoke(name,{...args,profile:profile.id})};
let meta=document.querySelector('meta[name=learner-id]');if(!meta){meta=document.createElement('meta');meta.name='learner-id';document.head.append(meta);}meta.content=profile.id;
invoke('current_profile').then(p=>{if(p?.id!==profile.id)location.replace('/index.html');});
window.addEventListener('DOMContentLoaded',()=>{
 document.getElementById('desktop-release')?.addEventListener('click',event=>{event.preventDefault();invoke('open_release').catch(e=>alert(String(e)));});
 const model=document.getElementById('tutor-model');if(model){for(const o of [...model.options])if(!['opencode-local','Qwen2.5-Coder-7B-Instruct-q4f16_1-MLC'].includes(o.value))o.remove();}
 document.getElementById('tutor-prepare-ai')?.remove();
 const apiSettings=document.getElementById('tutor-api-settings');if(apiSettings){for(const el of apiSettings.querySelectorAll('button,p'))el.remove();apiSettings.querySelector('input')?.closest('label')?.remove();}
 const header=document.body;
 const control=document.createElement('button');control.textContent=profile.name+' · Выйти';control.className='btn btn-link';control.style.cssText='position:fixed;bottom:10px;left:12px;z-index:10000;background:white;border:1px solid #ccddeb;border-radius:8px';
 control.onclick=async()=>{await invoke('logout');sessionStorage.removeItem('tutor-native-profile');location.replace('/index.html');};header.append(control);
 for(const id of ['pwa-install','pwa-install-nav','pwa-download','pwa-online','pwa-open']){const e=document.getElementById(id);if(e)e.hidden=true;}
 const status=document.getElementById('pwa-status');if(status)status.textContent='Курс установлен на этом компьютере.';
});
})();
