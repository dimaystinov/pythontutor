import {pipeline,env} from '../vendor/transformers/transformers.mjs';
env.allowLocalModels=true;env.allowRemoteModels=false;env.localModelPath=new URL('../models/',import.meta.url).href;env.useBrowserCache=true;
env.backends.onnx.wasm.wasmPaths=new URL('../vendor/transformers/',import.meta.url).href;
env.backends.onnx.wasm.numThreads=1;
let recognizer;
self.onmessage=async({data})=>{
 try{
  if(!recognizer)recognizer=await pipeline('automatic-speech-recognition','whisper-tiny',{device:'wasm',dtype:'q8',progress_callback:p=>self.postMessage({progress:p.progress===undefined?'Загрузка Whisper…':'Whisper: '+Math.round(p.progress)+'%'})});
  if(data.audio){const result=await recognizer(data.audio,{language:'russian',task:'transcribe',chunk_length_s:25,stride_length_s:4});self.postMessage({text:result.text});}
  else self.postMessage({ready:true});
 }catch(e){recognizer=null;self.postMessage({error:String(e.message||e)});}
};
