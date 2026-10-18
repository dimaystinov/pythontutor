const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
function element(tag){return{tag,children:[],hidden:false,disabled:false,style:{},append(...children){this.children.push(...children);},replaceChildren(){this.children=[];},setAttribute(k,v){this[k]=v;},removeAttribute(k){delete this[k];},click(){return this.onclick?.();}};}
test('Qwen settings start native download with progress, no file chooser or release link',async()=>{
 let progress,unlistened=false;const calls=[],created=[];
 const context={URL,WeakMap,document:{currentScript:{src:'https://test/static/pwa/model-assets.js'},getElementById:()=>null,querySelectorAll:()=>[],createElement:tag=>{created.push(tag);return element(tag);}},window:{TutorNative:{invoke:async name=>{calls.push(name);progress({payload:'Скачивание · 50%'});return '/models';}},__TAURI__:{event:{listen:async(_,fn)=>{progress=fn;return()=>unlistened=true;}},core:{convertFileSrc:()=> 'asset://models'}}}};
 vm.runInNewContext(fs.readFileSync('tutorial/static/pwa/model-assets.js','utf8'),context);
 const container=element('section');await context.window.TutorModelAssets.mount(container,'qwen7b',null,true);
 assert.deepEqual(calls,['prepare_model']);assert.ok(!created.includes('input'));assert.ok(!created.includes('a'));assert.equal(container.children.find(e=>e.tag==='progress').value,100);assert.match(container.children.at(-1).textContent,/установлен/);assert.ok(unlistened);
 await context.window.TutorModelAssets.cancel();assert.equal(calls.at(-1),'cancel_model');
});
test('failed automatic download leaves retry available, not file import',async()=>{
 const context={URL,WeakMap,document:{currentScript:{src:'https://test/static/pwa/model-assets.js'},getElementById:()=>null,querySelectorAll:()=>[],createElement:element},window:{TutorNative:{invoke:async()=>{throw Error('Нет сети');}},__TAURI__:{event:{listen:async()=>()=>{}}}}};
 vm.runInNewContext(fs.readFileSync('tutorial/static/pwa/model-assets.js','utf8'),context);const container=element('section');await context.window.TutorModelAssets.mount(container,'qwen7b',null,true);assert.match(container.children.at(-1).textContent,/Нет сети/);assert.equal(container.children[1].textContent,'Продолжить скачивание');assert.equal(container.children[1].disabled,false);
});
test('voice setup is placed in settings and one click starts installation',async()=>{
 const settings={before:()=>placed='settings'},chat={before:()=>placed='chat'};let placed,clickHandler,installs=0;const buttons=[element('button'),element('button'),element('button')],select={...element('select'),value:'0.3.0'},bar=element('progress'),note=element('p');let box;
 const context={URL,window:{TutorNative:{invoke:async name=>{if(name==='install_speech')installs++;if(name==='speech_active_version')return '0.3.0';if(name==='speech_installed_versions')return [];}},__TAURI__:{event:{listen:async()=>()=>{}}}},document:{currentScript:{src:'https://test/static/pwa/local-speech.js'},querySelectorAll:()=>[{addEventListener:(_,fn)=>clickHandler=fn}],getElementById:id=>id==='pwa-model-setup'?settings:id==='tutor-messages'?chat:id==='localspeech-setup'?box:null,createElement:tag=>{if(tag==='option')return element('option');box={style:{},querySelectorAll:()=>buttons,querySelector:s=>s==='select'?select:s==='progress'?bar:s==='[data-speech-version]'?element('p'):note};return box;}}};
 vm.runInNewContext(fs.readFileSync('tutorial/static/pwa/local-speech.js','utf8'),context);clickHandler();await new Promise(r=>setImmediate(r));assert.equal(placed,'settings');assert.equal(installs,1);assert.match(note.textContent,/готов/);
});
