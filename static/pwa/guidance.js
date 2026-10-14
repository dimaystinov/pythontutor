/* Reviewed lesson hints: available without a model or network. */
(function(){
'use strict';
function next(text,turns,hints){
 if(!Array.isArray(hints)||hints.length!==2||!hints.every(h=>typeof h.text==='string'&&h.text.trim()))return null;
 const request=text.toLowerCase().trim().replace(/[.!?]+$/,'');
 if(!/^(?:дай(?:те)?(?: небольшую| ещё одну| еще одну)? подсказку(?:, с чего начать\. не выдавай решение целиком)?|подсказка|ещ[её](?: одну)? подсказку|следующая подсказка|с чего начать(?: решение)?|покажи (?:первую|вторую) подсказку)$/.test(request))return null;
 const previous=turns.reduce((n,t)=>Math.max(n,Number(t.guidedHint)||0),0);
 const index=request.includes('первую')?1:request.includes('вторую')?2:Math.min(previous+1,3);
 if(index===3)return {guidedHint:3,answer:'Обе подсказки уже показаны. Попробуй применить их к маленькому примеру из условия. Если застрянешь, напиши, какой именно шаг непонятен.'};
 const hint=hints[index-1];
 return {guidedHint:index,answer:'Подсказка '+index+' из 2.\n\n'+hint.text+(hint.example?'\n\nПример отдельного действия:\n```python\n'+hint.example+'\n```':'')};
}
function current(text,turns){
 const source=document.getElementById('tutor-hints-data');
 try{return next(text,turns,JSON.parse(source?.textContent||'null'));}catch(_){return null;}
}
window.TutorGuidance={next,current};
})();
