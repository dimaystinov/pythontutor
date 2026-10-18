(function(){
'use strict';
if(!window.__TAURI__)return;
window.addEventListener('DOMContentLoaded',()=>{
 const host=document.getElementById('settings-app')?.closest('section');if(!host)return;
 const box=document.createElement('div');box.id='native-updates';
 box.innerHTML='<p>Установленная версия: <strong data-current>…</strong><br>Актуальная версия: <strong data-latest>не проверена</strong></p><div class="settings-actions"><button class="btn btn-default" data-check>Проверить обновления</button> <button class="btn btn-primary" data-install hidden>Скачать и установить обновление</button> <button class="btn btn-default" data-cancel hidden>Отменить</button> <button class="btn btn-default" data-quit hidden>Закрыть PythonTutor для обновления</button></div><progress max="100" value="0" hidden style="width:100%;margin-top:12px" aria-label="Скачивание обновления"></progress><p role="status" aria-live="polite"></p>';
 host.querySelector('h2').after(box);
 for(const id of ['desktop-release','desktop-download-options']){const e=document.getElementById(id);if(e)e.hidden=true;}
 const invoke=window.__TAURI__.core.invoke,current=box.querySelector('[data-current]'),latest=box.querySelector('[data-latest]'),check=box.querySelector('[data-check]'),install=box.querySelector('[data-install]'),cancel=box.querySelector('[data-cancel]'),bar=box.querySelector('progress'),note=box.querySelector('[role=status]');
 invoke('app_version').then(v=>current.textContent=v).catch(()=>current.textContent='не определена');
 check.onclick=async()=>{check.disabled=true;install.hidden=true;latest.textContent='проверяем…';note.textContent='';try{const s=await invoke('check_update');current.textContent=s.current;latest.textContent=s.latest||'не найдена';install.hidden=!s.available;note.textContent=s.available?'Доступно обновление.':'Установлена актуальная версия.';}catch(e){latest.textContent='не удалось проверить';note.textContent=String(e);}finally{check.disabled=false;}};
 install.onclick=async()=>{check.disabled=true;install.disabled=true;cancel.hidden=false;bar.hidden=false;bar.removeAttribute('value');note.textContent='Подключение…';let off;
 try{off=await window.__TAURI__.event.listen('update-progress',({payload:p})=>{if(p.total)bar.value=p.percent;else bar.removeAttribute('value');note.textContent=p.text+(p.total?' · '+p.percent+'% · '+(p.loaded/1048576).toFixed(1)+' из '+(p.total/1048576).toFixed(1)+' МБ':'');});note.textContent=await window.TutorNative.invoke('install_update');install.hidden=true;box.querySelector('[data-quit]').hidden=false;}
 catch(e){note.textContent=String(e);}finally{off?.();check.disabled=false;install.disabled=false;cancel.hidden=true;bar.hidden=true;}};
 cancel.onclick=()=>{note.textContent='Отмена скачивания…';invoke('cancel_update');};
 box.querySelector('[data-quit]').onclick=()=>invoke('finish_update');
 check.click();
});
})();
