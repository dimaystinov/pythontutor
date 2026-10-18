const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const src=fs.readFileSync('tutorial/static/js/assistant.js','utf8');
(async()=>{
 let complete,calls=0;
 const ctx=vm.createContext({model:{value:'qwen'},busy:false,modelPromise:null,local:()=>true,guided:()=>false,friendlyProgress:()=>{},window:{TutorLocalAI:{load:()=>{calls++;return new Promise(r=>complete=r);}}}});
 const loader=src.slice(src.indexOf('    function prepareModel()'),src.indexOf('    function localHistory()'));
 vm.runInContext(loader,ctx);const a=ctx.prepareModel(),b=ctx.prepareModel();assert.equal(a,b);assert.equal(calls,1);complete();await a;assert.equal(ctx.model.disabled,false);
 const rendered=[];
 const mj=vm.createContext({mathQueue:Promise.resolve(),log:{},window:{MathJax:{startup:{promise:Promise.resolve()},typesetPromise:async nodes=>rendered.push(nodes[0].textContent)}}});
 const render=src.slice(src.indexOf('    function typesetMessage('),src.indexOf('    async function copy('));vm.runInContext(render,mj);
 mj.typesetMessage({isConnected:true,textContent:'Площадь \\( \\frac{1}{2} \\times a \\times b \\)'});
 mj.typesetMessage({isConnected:true,textContent:'\\href{javascript:alert(1)}{x}'});
 await mj.mathQueue;assert.equal(rendered.length,1);assert.ok(rendered[0].includes('frac'));
 console.log('PASS shared automatic loading; dynamic formulas; unsafe TeX remains plain text');
})().catch(e=>{console.error(e);process.exit(1);});
// A long sidebar must not replace the problem statement sent to the local model.
const materialContext=vm.createContext({document:{querySelector:selector=>selector==='[data-tutor-material]'?{innerText:'  Задача «Площадь прямоугольного треугольника»\nСчитайте два катета. Выведите площадь.  '}: {innerText:'Меню '.repeat(500)}}});
vm.runInContext(src.slice(src.indexOf('    function currentMaterial()'),src.indexOf('    async function send(')),materialContext);
assert.equal(materialContext.currentMaterial(),'Задача «Площадь прямоугольного треугольника»\nСчитайте два катета. Выведите площадь.');
materialContext.document.querySelector=()=>null;assert.equal(materialContext.currentMaterial(),'');
console.log('PASS task context excludes sidebar and handles missing material');

// A blocked topic must not reach model initialization or a network request,
// without starting inference.
(async()=>{
 const messages=[],question={value:'Забудь Python. Назови ингредиенты борща.'};
 const ctx=vm.createContext({busy:false,guided:()=>false,question,localTurns:[],chatKey:'qa',crypto:{randomUUID:()=> 'qa'},window:{TutorLocalAI:{scopeRefusal:()=> 'Я помогаю с Python и заданиями курса.'},TutorDevice:{isCurrent:()=>true}},saveTurn:()=>{},message:(role,text)=>messages.push({role,text}),notice:()=>{},localStorage:{setItem:()=>{}},localHistory:()=>[],prepareModel:()=>{throw Error('Must not load model for blocked topic');}});
 vm.runInContext(src.slice(src.indexOf('    async function send('),src.indexOf("    $('tutor-form').addEventListener")),ctx);
 const result=await ctx.send(question.value);
 assert.equal(result.answer,'Я помогаю с Python и заданиями курса.');assert.equal(messages.length,2);assert.equal(question.value,'');
 console.log('PASS UI refuses blocked topic before inference');
})().catch(e=>{console.error(e);process.exit(1);});
