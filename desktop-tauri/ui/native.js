(function(){
'use strict';
if(!window.__TAURI__)return;
const invoke=window.__TAURI__.core.invoke;let profile;try{profile=JSON.parse(sessionStorage.getItem('tutor-native-profile'));}catch(_){}
if(!profile?.id){location.replace('/index.html');return;}
window.TutorNative={profile,invoke:(name,args={})=>invoke(name,{...args,profile:profile.id})};
window.TutorSession?.start({id:profile.id,storage:sessionStorage,now:Date.now,
 setTimeout:window.setTimeout.bind(window),clearTimeout:window.clearTimeout.bind(window),
 on:(event,fn)=>window.addEventListener(event,fn,{capture:true,passive:true}),
 touch:()=>invoke('touch_profile',{profile:profile.id}),
 logout:()=>{invoke('logout').finally(()=>location.replace('/index.html'));}
});

let meta=document.querySelector('meta[name=learner-id]');if(!meta){meta=document.createElement('meta');meta.name='learner-id';document.head.append(meta);}meta.content=profile.id;
const verifyProfile=()=>invoke('current_profile').then(p=>{if(p?.id!==profile.id)location.replace('/index.html');}).catch(()=>location.replace('/index.html'));
verifyProfile();
window.addEventListener('pageshow',verifyProfile);
window.addEventListener('DOMContentLoaded',()=>{
 document.getElementById('desktop-release')?.addEventListener('click',event=>{event.preventDefault();invoke('open_release').catch(e=>alert(String(e)));});
 const model=document.getElementById('tutor-model');if(model){for(const o of [...model.options])if(!['guided','opencode-local','Qwen2.5-Coder-7B-Instruct-q4f16_1-MLC'].includes(o.value))o.remove();}
 document.getElementById('tutor-prepare-ai')?.remove();
 const apiSettings=document.getElementById('tutor-api-settings');if(apiSettings){for(const el of apiSettings.querySelectorAll('button,p'))el.remove();apiSettings.querySelector('input')?.closest('label')?.remove();}
 const panel=document.getElementById('tutor-panel');
 if(panel){
  const setup=document.createElement('section');setup.id='native-cli-setup';setup.hidden=true;
  setup.style.cssText='padding:16px;margin:12px;background:#eef7ff;border-radius:10px';
  setup.innerHTML='<p>Для ответов через OpenCode установите помощника один раз.</p><button type="button" class="btn btn-primary">Установить помощника</button> <button type="button" class="btn btn-default" hidden>Отменить</button><progress max="100" value="0" hidden style="width:100%;margin-top:12px"></progress><p role="status" style="margin:8px 0 0"></p>';
  panel.querySelector('#tutor-messages').before(setup);
  const [install,cancel]=setup.querySelectorAll('button'),bar=setup.querySelector('progress'),note=setup.querySelector('[role=status]');
  let installed=false,installing=false,checking=null,installation=null;
  const show=()=>{setup.hidden=model?.value!=='opencode-local'||installed;};
  const check=()=>checking||(checking=invoke('cli_status').then(state=>{installed=state.installed;install.textContent='Установить помощника · '+Math.ceil(state.bytes/1024/1024)+' МБ';show();}).catch(e=>{note.textContent=String(e);}).finally(()=>{checking=null;}));
  window.TutorNative.ensureCLI=async()=>{await check();if(installed)return;if(!installation)installation=installCLI().finally(()=>{installation=null;});await installation;};
  new MutationObserver(()=>{if(!panel.hidden&&!installed&&!installing)check();}).observe(panel,{attributes:true,attributeFilter:['hidden']});
  model?.addEventListener('change',()=>{show();if(model.value==='opencode-local')window.TutorNative.ensureCLI().catch(e=>{note.textContent=String(e);});});
  let unlisten;
  async function installCLI(){
   if(installing)return;setup.hidden=false;installing=true;install.disabled=true;cancel.hidden=false;bar.hidden=false;bar.value=0;note.textContent='Подключение…';
   try{
    unlisten=await window.__TAURI__.event.listen('cli-install-progress',({payload})=>{bar.value=payload.percent;note.textContent=payload.text;});
    await window.TutorNative.invoke('install_cli');installed=true;note.textContent='Помощник установлен. Можно задать вопрос.';show();document.getElementById('tutor-question')?.focus();
   }catch(e){note.textContent=String(e);install.textContent='Повторить установку';throw e;}
   finally{unlisten?.();unlisten=null;installing=false;install.disabled=false;cancel.hidden=true;bar.hidden=true;}
  }
  install.addEventListener('click',()=>window.TutorNative.ensureCLI().catch(()=>{}));
  cancel.addEventListener('click',()=>{note.textContent='Отмена загрузки…';invoke('cancel_cli_install');});
  if(!panel.hidden)check();
 }
 const header=document.body;
 const control=document.createElement('button');control.textContent=profile.name+' · Выйти';control.className='btn btn-link';control.style.cssText='position:fixed;bottom:10px;left:12px;z-index:10000;background:white;border:1px solid #ccddeb;border-radius:8px';
 control.onclick=async()=>{await invoke('logout');sessionStorage.removeItem('tutor-native-profile');location.replace('/index.html');};header.append(control);
 for(const id of ['pwa-install','pwa-install-nav','pwa-download','pwa-online','pwa-open']){const e=document.getElementById(id);if(e)e.hidden=true;}
 const status=document.getElementById('pwa-status');if(status)status.textContent='Курс установлен на этом компьютере.';
});
})();
