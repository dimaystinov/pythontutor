(function(){
'use strict';
let worker,pending,speechEnd;
function operation(audio,progress){
 if(pending)return Promise.reject(Error('Дождитесь распознавания речи.'));
 if(!worker)worker=new Worker('/pythontutor-selfhost/static/pwa/voice-worker.mjs',{type:'module'});
 return new Promise((resolve,reject)=>{const timer=setTimeout(()=>{worker.terminate();worker=null;pending=null;reject(Error('Не удалось загрузить или запустить распознавание речи. Повторите с подключением к сети.'));},300000);
 pending=true;worker.onmessage=({data})=>{if(data.progress){progress?.(data.progress);return;}clearTimeout(timer);pending=null;if(data.error)reject(Error(data.error));else resolve(data);};worker.onerror=e=>{clearTimeout(timer);pending=null;worker.terminate();worker=null;reject(Error(e.message||'Ошибка локального распознавания.'));};worker.postMessage({audio});});
}
async function prepare(progress){await operation(null,progress);progress?.('Whisper готов: голосовой ввод работает локально.');}
async function transcribe(chunks,sampleRate,progress){
 // The AudioWorklet already resamples microphone audio to 16 kHz.
 const length=chunks.reduce((n,c)=>n+c.length,0),audio=new Float32Array(length);let offset=0;
 for(const c of chunks){for(let i=0;i<c.length;i++)audio[offset+i]=c[i]/32768;offset+=c.length;}
 const result=await operation(audio,progress);if(!result.text?.trim())throw Error('Речь не распознана. Повторите или напишите вопрос.');return result.text;
}
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
