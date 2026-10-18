const test=require('node:test'),assert=require('node:assert/strict');
const adapter=require('../pwa/speech-adapter.js');
test('SDK receives bounded normalized PCM, waits for final flush and deduplicates segments',async()=>{
 const listeners={};let disposed=false,inFlight=false,writes=0;
 const sdk={create:()=>({on:(event,fn)=>listeners[event]=fn,start:async o=>assert.equal(o.input,'pcm'),write:async(samples,rate)=>{assert.equal(inFlight,false);inFlight=true;assert.ok(samples.length<=16000);assert.equal(rate,16000);assert.equal(samples[0],-1);writes++;await Promise.resolve();inFlight=false;},stop:async()=>{listeners.final({sessionId:'s',segmentId:1,rawText:'проверка'});listeners.final({sessionId:'s',segmentId:1,rawText:'проверка'});await Promise.resolve();listeners.final({sessionId:'s',segmentId:2,rawText:'связи'});},dispose:async()=>disposed=true})};
 assert.equal(await adapter.transcribe(sdk,{},[new Int16Array(32001).fill(-32768)]),'проверка связи');assert.equal(writes,3);assert.ok(disposed);
});
test('SDK errors cannot become a successful transcript and resources are disposed',async()=>{
 let error,disposed=false;const sdk={create:()=>({on:(e,f)=>{if(e==='error')error=f;},start:async()=>{},write:async()=>{},stop:async()=>error({message:'broken model'}),dispose:async()=>disposed=true})};
 await assert.rejects(adapter.transcribe(sdk,{},[]),/broken model/);assert.ok(disposed);
});
