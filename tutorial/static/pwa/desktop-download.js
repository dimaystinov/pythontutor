(function(root){
'use strict';
const base='https://github.com/dimaystinov/pythontutor/releases/download/app-v2.3.1/';
const files={windows:'PythonTutor_2.3.1_x64-setup.exe',arm:'PythonTutor_2.3.1_aarch64.dmg'};
function detect(info){
 const platform=info.platform||'',ua=info.ua||'';
 if(/Android|iPhone|iPad|iPod/i.test(ua)||(/Mac/i.test(platform)&&info.touch>1))return null;
 if(/Win/i.test(platform+' '+ua))return 'windows';
 if(!/Mac/i.test(platform+' '+ua))return null;
 if(/arm|aarch64/i.test(info.arch||''))return 'arm';
 if(/x86|x64/i.test(info.arch||''))return null;
 // Safari does not expose CPU architecture; use a named GPU only when available.
 if(/Apple M\d/i.test(info.renderer||''))return 'arm';
 if(/Intel|AMD|Radeon|NVIDIA/i.test(info.renderer||''))return null;
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
 if(selected){button.href=base+files[selected];button.textContent='Скачать для '+({windows:'Windows',arm:'macOS · Apple Silicon'}[selected]);}
 else{button.textContent=/Mac/i.test(info.platform||'')&&info.touch<=1?'Выбрать версию для Mac':'Выбрать установщик';}
 // Refresh only to a complete app release; never navigate to a release listing.
 try {
  const response=await fetch('https://api.github.com/repos/dimaystinov/pythontutor/releases?per_page=100',{signal:AbortSignal.timeout(8000)});
  if(!response.ok)return;
  const releases=await response.json();
  const ready=releases.filter(r=>!r.draft&&!r.prerelease&&/^app-v\d+\.\d+\.\d+$/.test(r.tag_name)&&['x64-setup.exe','aarch64.dmg'].every(suffix=>r.assets.some(a=>a.name==='PythonTutor_'+r.tag_name.slice(5)+'_'+suffix&&a.size>0)));
  ready.sort((a,b)=>{const av=a.tag_name.slice(5).split('.').map(Number),bv=b.tag_name.slice(5).split('.').map(Number);return bv[0]-av[0]||bv[1]-av[1]||bv[2]-av[2];});
  const release=ready[0];if(!release)return;
  const suffix={windows:'x64-setup.exe',arm:'aarch64.dmg'};
  function direct(kind){const name='PythonTutor_'+release.tag_name.slice(5)+'_'+suffix[kind];const expected='https://github.com/dimaystinov/pythontutor/releases/download/'+release.tag_name+'/'+name;return release.assets.some(a=>a.name===name&&a.browser_download_url===expected)?expected:null;}
  if(selected&&direct(selected))button.href=direct(selected);
  ['windows','arm'].forEach((kind,index)=>{const link=choices.querySelectorAll('a')[index];if(link&&direct(kind))link.href=direct(kind);});
 }catch(_){} // Keep the last verified direct installer link offline.
})();
})(typeof window==='undefined'?globalThis:window);
