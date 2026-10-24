const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const root=path.resolve(__dirname,'../..');
const read=p=>fs.readFileSync(path.join(root,p),'utf8');
function storage(){const data=new Map();return {getItem:k=>data.get(k)??null,setItem:(k,v)=>data.set(k,String(v)),removeItem:k=>data.delete(k),key:i=>[...data.keys()][i],get length(){return data.size;}};}
test('problem editor reads the active profile draft instead of shared local draft',()=>{
 const localStorage=storage();
 localStorage.setItem('problem-draft:local:apples',JSON.stringify({solution:{code:'OTHER STUDENT',stdin:''}}));
 localStorage.setItem('problem-draft:alice:apples',JSON.stringify({solution:{code:'ALICE',stdin:''}}));
 let loaded;
 const stop=new Error('editor captured');
 const $=value=>{if(typeof value==='function')return value();return {text:()=>'',attr:()=> 'local'};};
 const context={$,localStorage,problem_name:'apples',window:{TutorDevice:{owner:()=> 'alice'}},Visualizer:function(_,code){loaded=code;throw stop;}};
 assert.throws(()=>vm.runInNewContext(read('static/js/problem.js'),context),e=>e===stop);
 assert.equal(loaded,'ALICE');
});
test('native reset is isolated, survives reopen and does not need browser IndexedDB',async()=>{
 const localStorage=storage(),rows=new Map();
 function page(id){
  const native={profile:{id},invoke:async(name,args)=>{
   if(name==='solutions')return [...rows.values()].filter(r=>r.owner===id);
   if(name==='save_solution')rows.set(args.data.key,structuredClone(args.data));
   if(name==='reset_progress')for(const [k,r] of rows)if(r.owner===id)rows.delete(k);
  }};
  const context={window:{TutorNative:native,dispatchEvent(){}},TutorNative:native,localStorage,document:{querySelector:()=>({content:id})},Event:class{}};
  vm.runInNewContext((process.env.TUTOR_TEST_BUNDLE ? fs.readFileSync(path.join(root,'../desktop-tauri/frontend/pythontutor/static/pwa/storage.js'),'utf8') : read('static/pwa/storage.js')),context);return context.window.TutorDevice;
 }
 const a=page('alice'),old=page('alice'),b=page('bob');
 await a.save('problem','apples','a',{status:'ok'});
 await b.save('problem','apples','b',{status:'ok'});
 localStorage.setItem('problem-draft:alice:apples','a');localStorage.setItem('tutor-local-chat:alice:shared','chat');
 localStorage.setItem('problem-draft:bob:apples','b');localStorage.setItem('tutor-ai-model','guided');
 await a.reset();
 assert.equal((await page('alice').list()).length,0);
 assert.equal((await page('bob').get('problem','apples')).code,'b');
 assert.equal(localStorage.getItem('problem-draft:alice:apples'),null);
 assert.equal(localStorage.getItem('tutor-local-chat:alice:shared'),null);
 assert.equal(localStorage.getItem('problem-draft:bob:apples'),'b');
 assert.equal(localStorage.getItem('tutor-ai-model'),'guided');
 await assert.rejects(old.save('problem','apples','old',{status:'ok'}),/Прогресс очищен/);
 await page('alice').save('problem','apples','wrong',{status:'error'});
 assert.equal((await page('alice').get('problem','apples')).solved,false);
});
test('local menu clears stale solved marks when there are no stored solutions',async()=>{
 const classes=new Set(['solved']);
 const a={title:'Задача решена',getAttribute:()=>'/problems/apples/',matches:()=>true,classList:{remove(){}},parentElement:{classList:{remove:(...xs)=>xs.forEach(x=>classes.delete(x)),contains:x=>classes.has(x),add:x=>classes.add(x)}},removeAttribute(){this.title='';}};
 const source=read('static/pwa/app.js');
 const fn=source.slice(source.indexOf('async function restoreProgress(){'),source.indexOf('\nrestoreProgress().catch'));
 const context={local:true,localStorage:storage(),TutorDevice:{list:async()=>[],owner:()=> 'bob'},document:{querySelector:()=>null,querySelectorAll:()=>[a],getElementById:()=>null},window:{},$:()=>null};
 vm.runInNewContext(fn+'\nthis.restore=restoreProgress;',context);await context.restore();
 assert.equal(classes.has('solved'),false);
});
test('returning to a cached page from another account returns to login',async()=>{
 let active={id:'alice'},redirect;const events={};
 const context={sessionStorage:{getItem:()=>JSON.stringify({id:'alice'})},location:{replace:url=>redirect=url},document:{querySelector:()=>({content:'local'})},window:{__TAURI__:{core:{invoke:async()=>active}},addEventListener:(name,fn)=>events[name]=fn}};
 vm.runInNewContext(fs.readFileSync(path.join(root,'../desktop-tauri/ui/native.js'),'utf8'),context);
 await new Promise(r=>setImmediate(r));assert.equal(redirect,undefined);
 active={id:'bob'};events.pageshow?.();await new Promise(r=>setImmediate(r));
 assert.equal(redirect,'/index.html');
});
