(function(root){
'use strict';
const base='https://github.com/dimaystinov/pythontutor/releases/download/app-v2.0.6/';
const files={windows:'PythonTutor_2.0.6_x64-setup.exe',arm:'PythonTutor_2.0.6_aarch64.dmg',intel:'PythonTutor_2.0.6_x64.dmg'};
function detect(info){
 const platform=info.platform||'',ua=info.ua||'';
 if(/Android|iPhone|iPad|iPod/i.test(ua)||(/Mac/i.test(platform)&&info.touch>1))return null;
 if(/Win/i.test(platform+' '+ua))return 'windows';
 if(!/Mac/i.test(platform+' '+ua))return null;
 if(/arm|aarch64/i.test(info.arch||''))return 'arm';
 if(/x86|x64/i.test(info.arch||''))return 'intel';
 // Safari does not expose CPU architecture; use a named GPU only when available.
 if(/Apple M\d/i.test(info.renderer||''))return 'arm';
 if(/Intel|AMD|Radeon|NVIDIA/i.test(info.renderer||''))return 'intel';
 return null;
}
if(typeof module==='object'&&module.exports){module.exports={detect,files,base};return;}
const button=document.getElementById('desktop-release'),choices=document.getElementById('desktop-download-options');
if(!button)return;
let selected=null;
button.addEventListener('click',event=>{
 if(!selected){event.preventDefault();choices.open=true;choices.querySelector('a')?.focus();}
});
(async()=>{
 const info={platform:navigator.userAgentData?.platform||navigator.platform,ua:navigator.userAgent,touch:navigator.maxTouchPoints};
 try{const hints=await Promise.race([navigator.userAgentData?.getHighEntropyValues(['architecture']),new Promise(resolve=>setTimeout(resolve,800))]);info.arch=hints?.architecture;}catch(_){}
 if(/Mac/i.test(info.platform||'')&&!info.arch){
  try{const canvas=document.createElement('canvas'),gl=canvas.getContext('webgl');const ext=gl?.getExtension('WEBGL_debug_renderer_info');if(ext)info.renderer=gl.getParameter(ext.UNMASKED_RENDERER_WEBGL);gl?.getExtension('WEBGL_lose_context')?.loseContext();}catch(_){}
 }
 selected=detect(info);
 if(selected){button.href=base+files[selected];button.textContent='Скачать для '+({windows:'Windows',arm:'macOS · Apple Silicon',intel:'macOS · Intel'}[selected]);}
 else{button.textContent=/Mac/i.test(info.platform||'')&&info.touch<=1?'Выбрать версию для Mac':'Выбрать установщик';}
})();
})(typeof window==='undefined'?globalThis:window);
