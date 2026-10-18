const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('desktop-tauri/frontend/pythontutor/static/pwa/storage.js','utf8');
const rows=new Map();
function learner(id){const storage=new Map();const native={invoke:async(name,args)=>{if(name==='solutions')return [...rows.values()].filter(x=>x.owner===id);if(name==='save_solution')rows.set(args.data.key,structuredClone(args.data));}};const context={window:{TutorNative:native,dispatchEvent(){}},TutorNative:native,document:{querySelector:()=>({content:id})},localStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v)},Event:class{},Date,Math};vm.runInNewContext(source,context);return context.window.TutorDevice;}
(async()=>{const a=learner('alice'),b=learner('bob');await a.save('problem','apples','print(3)',{status:'ok'});assert.equal((await a.list()).length,1);assert.equal((await b.list()).length,0);await b.save('problem','apples','print(2)',{status:'error'});assert.equal((await a.get('problem','apples')).code,'print(3)');assert.equal((await b.get('problem','apples')).solved,false);await a.save('problem','apples','print(4)',{status:'error'});assert.equal((await a.get('problem','apples')).acceptedCode,'print(3)');console.log('PASS native SQLite adapter: per-profile isolation, accepted solution retained');})();

const settings=fs.readFileSync('desktop-tauri/frontend/pythontutor/pwa/index.html','utf8');
assert.ok(!settings.includes('id="pwa-download"'));
assert.ok(!settings.includes('Скачайте курс один раз'));
assert.ok(settings.includes('settings-assistant'));
console.log('PASS bundled Settings omit redundant course download');
