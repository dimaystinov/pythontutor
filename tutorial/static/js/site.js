/* Send Django CSRF tokens only to same-origin, state-changing requests. */
(function ($) {
    $.ajaxPrefilter(function (options, original, xhr) {
        if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(options.type) && !options.crossDomain) {
            var token = document.querySelector('meta[name="csrf-token"]');
            if (token) xhr.setRequestHeader('X-CSRFToken', token.content);
        }
    });
})(jQuery);

// Bind once to the document: lesson renderers may replace heading/button nodes.
(function(){
 function sync(){
  const sidebar=document.querySelector('.sidebar');if(!sidebar)return;
  const open=!document.body.classList.contains('lesson-menu-hidden');
  sidebar.hidden=!open;
  document.querySelectorAll('.sidebar-toggle').forEach(button=>{
   button.setAttribute('aria-expanded',String(open));
   button.setAttribute('aria-label',open?'Скрыть меню уроков':'Показать меню уроков');
   const icon=button.querySelector('i');if(icon){icon.classList.toggle('fa-angle-left',open);icon.classList.toggle('fa-angle-right',!open);}
  });
 }
 document.addEventListener('click',event=>{
  if(!event.target.closest?.('.sidebar-toggle')||!document.querySelector('.sidebar'))return;
  event.preventDefault();
  const hidden=document.body.classList.toggle('lesson-menu-hidden');
  try{localStorage.setItem('lesson-menu-open',hidden?'no':'yes');}catch(_){}
  sync();window.dispatchEvent(new Event('resize'));
 });
 function init(){try{document.body.classList.toggle('lesson-menu-hidden',localStorage.getItem('lesson-menu-open')==='no');}catch(_){}sync();}
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
