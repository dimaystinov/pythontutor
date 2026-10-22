const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
async function run(installed){
 class Element{constructor(tag){this.tag=tag;this.style={};this.children=[];this.value='';this.hidden=false;}append(...els){for(const e of els){e.parentNode=this;this.children.push(e);}}remove(){if(this.parentNode){const p=this.parentNode;p.children=p.children.filter(e=>e!==this);this.parentNode=null;}}setAttribute(){}removeAttribute(){}after(){}closest(){return this.parentNode;}get options(){return this.children;}dispatchEvent(){}}
 const section=new Element('section'),heading=new Element('h2'),select=new Element('select');section.append(heading);
 for(const value of ['guided','Qwen2.5-Coder-7B-Instruct-q4f16_1-MLC','opencode-local']){const o=new Element('option');o.value=value;select.append(o);}
 const events={},calls=[];let state=installed;
 const window={__TAURI__:{event:{listen:async()=>()=>{}}},TutorNative:{invoke:async name=>{calls.push(name);if(name.endsWith('_status'))return {installed:state,bytes:100};if(name==='install_cli')state=true;}},TutorSpeech:{ready:async()=>state,prepare:async cb=>{cb('50%');state=true;}},TutorModelAssets:{ensure:async(id,cb)=>{cb('Скачивание · 50%');state=true;},remove:async()=>{state=false;}},addEventListener:(n,cb)=>events[n]=cb,dispatchEvent(){} };
 vm.runInNewContext(fs.readFileSync('desktop-tauri/ui/components.js','utf8'),{window,document:{getElementById:id=>id==='tutor-model'?select:id==='settings-assistant'?heading:null,createElement:t=>new Element(t)},localStorage:{getItem:()=>null},Event:class{}});
 await events.DOMContentLoaded();return {select,section,calls};
}
test('only installed assistants appear; settings install and remove Qwen with status',async()=>{
 const a=await run(false);assert.deepEqual(a.select.options.map(o=>o.value),['guided']);
 const card=a.section.children.find(e=>e.tag==='section'),buttons=card.children.filter(e=>e.tag==='button'),note=card.children[2];
 assert.match(note.textContent,/Не установлен/);await buttons[0].onclick();assert.match(note.textContent,/Установлен/);assert.equal(a.select.options.length,2);await buttons[1].onclick();assert.equal(a.select.options.length,1);assert.match(note.textContent,/Не установлен/);
});
test('installed optional assistants are selectable after restarting settings',async()=>{const a=await run(true);assert.equal(a.select.options.length,3);});
