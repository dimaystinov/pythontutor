const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const records=new Map([
 ['local:problem:sum',{key:'local:problem:sum',owner:'local',solved:true}],
 ['teacher:problem:sum',{key:'teacher:problem:sum',owner:'teacher',solved:true}]
]);
const data=new Map([
 ['problem-draft:local:sum','code'],['image-draft:local:hsv','code'],
 ['tutor-local-chat:local:/task','chat'],['problem-draft:teacher:sum','other'],
 ['tutor-ai-model','qwen'],['lesson-menu-open','true']
]);
const db={transaction(){const tx={objectStore(){return {
 getAll(){return {result:[...records.values()]};}, delete(key){records.delete(key);}
 };}};queueMicrotask(()=>tx.oncomplete());return tx;}};
const context={window:{},document:{querySelector:()=>({content:'local'})},
 indexedDB:{open(){const r={result:db};queueMicrotask(()=>r.onsuccess());return r;}},
 localStorage:{get length(){return data.size;},key:i=>[...data.keys()][i],removeItem:k=>data.delete(k),setItem:(k,v)=>data.set(k,v)}
};
vm.runInNewContext(fs.readFileSync(require('node:path').join(__dirname,'../pwa/storage.js'),'utf8'),context);
(async()=>{
 await context.window.TutorDevice.reset();
 assert.equal(records.has('local:problem:sum'),false);
 assert.equal(records.has('teacher:problem:sum'),true);
 assert.equal(data.has('problem-draft:local:sum'),false);
 assert.equal(data.has('image-draft:local:hsv'),false);
 assert.equal(data.has('tutor-local-chat:local:/task'),false);
 assert.equal(data.get('problem-draft:teacher:sum'),'other');
 assert.equal(data.get('tutor-ai-model'),'qwen');
 assert.ok(data.get('tutor-progress-reset:local'));
 console.log('Reset removes current learner progress and chats, preserves other owners and model settings, signals other tabs.');
})().catch(e=>{console.error(e);process.exitCode=1;});
