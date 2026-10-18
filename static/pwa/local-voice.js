(function(){
'use strict';
let speechEnd;
function sdk(){if(!window.TutorSpeech)throw Error('Голосовой ввод LocalSpeech не загрузился. Перезагрузите страницу.');return window.TutorSpeech;}
async function prepare(progress){return sdk().prepare(progress);}
async function transcribe(chunks,sampleRate,progress){return sdk().transcribe(chunks,sampleRate,progress);}
function stop(){window.speechSynthesis?.cancel();if(speechEnd){speechEnd();speechEnd=null;}}
async function speak(text){
 if(!window.speechSynthesis)throw Error('На устройстве недоступна озвучка. Ответ сохранён в чате.');
 let voices=speechSynthesis.getVoices();if(!voices.length){await new Promise(r=>setTimeout(r,500));voices=speechSynthesis.getVoices();}
 const voice=voices.find(v=>v.localService&&/^ru/i.test(v.lang));
 if(!voice)throw Error('Для офлайн-озвучки установите русский системный голос. Ответ доступен в чате.');
 stop();return new Promise((resolve,reject)=>{speechEnd=resolve;const u=new SpeechSynthesisUtterance(text.replace(/```[\s\S]*?```/g,'Код приведён в чате.'));u.voice=voice;u.lang='ru-RU';u.onend=()=>{speechEnd=null;resolve();};u.onerror=()=>{speechEnd=null;reject(Error('Не удалось озвучить ответ.'));};speechSynthesis.speak(u);});
}
window.TutorLocalVoice={prepare,transcribe,speak,stop};
})();
