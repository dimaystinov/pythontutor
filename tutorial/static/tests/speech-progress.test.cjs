const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),{webcrypto}=require('node:crypto');
test('speech download reports intermediate bytes, verifies and reuses cached files',async()=>{
 const bytes=new Uint8Array([1,2,3,4]),sha=Buffer.from(await webcrypto.subtle.digest('SHA-256',bytes)).toString('hex');
 const data=new Map(),events=[];let downloads=0;
 const manifest={files:[{path:'models/small/test.onnx',bytes:4,sha256:sha}]};
 const ctx={URL,Response,Uint8Array,AbortController,crypto:webcrypto,navigator:{serviceWorker:{controller:{}}},window:{},document:{currentScript:{src:'https://example.test/static/pwa/local-speech.js'},querySelectorAll:()=>[]},caches:{open:async()=>({match:async k=>data.get(String(k))?.clone(),put:async(k,r)=>data.set(String(k),r)})},fetch:async url=>{if(String(url).endsWith('manifest.json'))return new Response(JSON.stringify(manifest));downloads++;return new Response(new ReadableStream({start(c){c.enqueue(bytes.slice(0,2));c.enqueue(bytes.slice(2));c.close();}}));}};
 vm.runInNewContext(fs.readFileSync('tutorial/static/pwa/local-speech.js','utf8'),ctx);
 await ctx.window.TutorSpeech.install((percent,info)=>events.push({percent,...info}));
 assert.ok(events.some(e=>e.loaded===2&&e.percent===50));assert.equal(events.at(-1).percent,100);assert.equal(await ctx.window.TutorSpeech.ready(),true);
 await ctx.window.TutorSpeech.install();assert.equal(downloads,1);
});
test('existing AI preference migrates once, later explicit choice survives',()=>{
 const source=fs.readFileSync('tutorial/static/js/assistant.js','utf8');const init=source.slice(source.indexOf('    try {'),source.indexOf('    const guided='));
 const prefs=new Map([['tutor-ai-model','opencode-local']]);const ctx={model:{value:'',querySelector:()=>true},localStorage:{getItem:k=>prefs.get(k),setItem:(k,v)=>prefs.set(k,v)}};
 vm.runInNewContext(init,ctx);assert.equal(ctx.model.value,'guided');prefs.set('tutor-ai-model','opencode-local');vm.runInNewContext(init,ctx);assert.equal(ctx.model.value,'opencode-local');
});
