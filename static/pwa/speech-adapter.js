/* LocalSpeech SDK v1 host contract: PCM16 -> Float32, bounded writes, final events only. */
(function(root){
async function transcribe(sdk,options,chunks){
 const client=sdk.create(options),finals=new Map();let failure;
 client.on('final',e=>finals.set(e.sessionId+':'+e.segmentId,e.rawText||''));
 client.on('error',e=>{failure=e.message||'Ошибка LocalSpeech.';});
 try{
  await client.start({input:'pcm'});
  for(const chunk of chunks)for(let i=0;i<chunk.length;i+=16000){
   if(failure)throw Error(failure);
   await client.write(Float32Array.from(chunk.subarray(i,i+16000),n=>n/32768),16000);
  }
  await client.stop();if(failure)throw Error(failure);
  const text=[...finals.values()].join(' ').trim();if(!text)throw Error('Речь не распознана. Повторите или напишите вопрос.');return text;
 }finally{await client.dispose();}
}
if(typeof module==='object'&&module.exports)module.exports={transcribe};else root.TutorSpeechAdapter={transcribe};
})(typeof window==='undefined'?globalThis:window);
