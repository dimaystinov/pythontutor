const {test}=require('node:test');const assert=require('node:assert/strict');const vm=require('node:vm');const fs=require('node:fs');
function setup(){
 const root='https://example.test/pythontutor/';
 const data=new Map([
 ['webllm/model',new Set([root+'static/models/qwen7b/params.bin',root+'static/models/another/params.bin'])],
 ['transformers-cache',new Set([root+'static/models/whisper-tiny/onnx/a.onnx',root+'static/models/another/a.onnx'])],
 ['local-speech-verified-v1',new Set([root+'static/local-speech/0.3.0/models/small/a.onnx?sha256=x', 'https://example.test/other/speech/model.onnx'])],
 ['course-offline',new Set([root+'lessons/',root+'static/models/qwen7b/keep'])]
 ]);const calls=[];const preferences=new Map([["tutor-ai-model","Qwen2.5-Coder-7B-Instruct-q4f16_1-MLC"]]);
 const context={localStorage:{getItem:key=>preferences.get(key),setItem:(key,value)=>preferences.set(key,value)},URL,CustomEvent:class{},window:{dispatchEvent(){},TutorNative:{invoke:async name=>calls.push(name)}},document:{currentScript:{src:root+'static/pwa/model-assets.js'},querySelectorAll:()=>[],getElementById:()=>null},caches:{keys:async()=>[...data.keys()],open:async name=>({keys:async()=>[...data.get(name)].map(url=>({url})),delete:async r=>data.get(name).delete(r.url)})}};
 vm.runInNewContext(fs.readFileSync('tutorial/static/pwa/model-assets.js','utf8'),context);return{data,calls,preferences,remove:context.window.TutorModelAssets.remove,root};
}
test('deletes selected Qwen files only, including native disk request',async()=>{const {data,calls,remove,root}=setup();await remove('qwen7b');assert.deepEqual(calls,['remove_model']);assert.deepEqual([...data.get('webllm/model')],[root+'static/models/another/params.bin']);assert.equal(data.get('course-offline').size,2);assert.equal(data.get('transformers-cache').size,2);});
test('speech cleanup does not remove course, other apps or other model caches',async()=>{const {data,remove}=setup();await remove('localspeech');assert.equal(data.get('local-speech-verified-v1').size,1);await remove('whisper-tiny');assert.equal(data.get('transformers-cache').size,1);assert.equal(data.get('webllm/model').size,2);assert.equal(data.get('course-offline').size,2);await remove('localspeech');});
test('unknown component cannot choose arbitrary deletion target',async()=>{const {remove,calls}=setup();await assert.rejects(()=>remove('../profiles'));assert.equal(calls.length,0);});
test('OpenCode deletion does not access web data',async()=>{const {remove,calls,data}=setup();await remove('opencode');assert.deepEqual(calls,['remove_cli']);assert.equal(data.get('course-offline').size,2);});

test("deleting the selected model prevents automatic redownload",async()=>{const {remove,preferences}=setup();await remove("qwen7b");assert.equal(preferences.get("tutor-ai-model"),"guided");});
