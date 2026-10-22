const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
test('native OpenCode bypasses loopback, installs CLI and sends the selected model',async()=>{
 const calls=[],elements={'tutor-api-model':{value:'big-pickle'}};
 const window={TutorNative:{ensureCLI:async()=>calls.push('install'),invoke:async(name,args)=>{calls.push({name,args});return 'Разберём деление.';}}};
 vm.runInNewContext(fs.readFileSync('tutorial/static/pwa/local-ai.js','utf8'),{window,document:{getElementById:id=>elements[id]},location:{origin:'http://tauri.localhost'},setTimeout,clearTimeout,AbortController});
 assert.match(await window.TutorLocalAI.answer('opencode-local',{question:'Что такое деление?',context:'Задача',turns:[]}),/деление/);
 assert.equal(calls[0],'install');assert.equal(calls[1].args.model,'big-pickle');
 window.TutorLocalAI.stop();assert.equal(calls.at(-1).name,'cancel_chat');
});
test('changing tasks keeps conversation but excludes previous task hints',()=>{
 const source=fs.readFileSync('tutorial/static/js/assistant.js','utf8');
 const ctx={panel:{dataset:{url:'/new'}},localHistory:()=>[{task:'/old',guidedHint:1,answer:'old hint'},{task:'/old',answer:'conversation'},{task:'/new',guidedHint:1,answer:'new hint'}]};
 vm.runInNewContext(source.slice(source.indexOf('    function visibleHistory()'),source.indexOf('    function saveTurn(')),ctx);
 assert.deepEqual(Array.from(ctx.visibleHistory(),t=>t.answer),['conversation','new hint']);
});
test('voice preparation automatically downloads once and reports progress',async()=>{
 const src=fs.readFileSync('tutorial/static/pwa/local-speech.js','utf8'),events=[];let installs=0,finish;
 const ctx={activeVersion:async()=> '0.3.0',ready:async()=>false,install:async cb=>{installs++;cb(35);await new Promise(r=>finish=r);cb(100);}};
 vm.runInNewContext(src.slice(src.indexOf('let preparing;'),src.indexOf('async function dispose()')),ctx);
 const a=ctx.prepare(t=>events.push(t)),b=ctx.prepare();await new Promise(r=>setImmediate(r));assert.equal(installs,1);finish();await Promise.all([a,b]);assert.ok(events.some(t=>t.includes('35%')));
});
test('voice conversation starts after preparation without resetting stored turns',async()=>{
 const src=fs.readFileSync('tutorial/static/js/assistant.js','utf8'),calls=[],button={classList:{add(){}}};
 const ctx={callActive:false,busy:false,epoch:0,$:()=>button,local:()=>true,voiceStatus:()=>{},prepareModel:async()=>calls.push('model'),friendlyProgress:()=>{},window:{TutorLocalVoice:{prepare:async()=>calls.push('voice')}},startRecording:async()=>calls.push('record'),stopCall:()=>calls.push('failure')};
 vm.runInNewContext(src.slice(src.indexOf('    async function beginCall()'),src.indexOf("    $('tutor-call').addEventListener")),ctx);
 await ctx.beginCall();assert.deepEqual(calls,['model','voice','record']);
});

test('selecting Qwen starts preparation and reports failure without sending a question',async()=>{
 const src=fs.readFileSync('tutorial/static/js/assistant.js','utf8'),events=[];
 const ctx={requestEpoch:0,stopCall(){},window:{TutorLocalAI:{stop(){}}},modelPromise:null,loaded:true,localStorage:{setItem(){}},model:{value:'Qwen'},describeModel(){},history(){},guided:()=>false,friendlyProgress:t=>events.push(t),prepareModel:async()=>{events.push('prepare');throw Error('WebGPU unavailable');},$:()=>({hidden:false}),notice:t=>events.push(t)};
 vm.runInNewContext(src.slice(src.indexOf('    async function changeModel()'),src.indexOf("    model?.addEventListener('change',changeModel)")),ctx);
 await ctx.changeModel();assert.equal(events[1],'prepare');assert.equal(events.at(-1),'WebGPU unavailable');
});
