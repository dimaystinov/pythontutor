const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const source=fs.readFileSync('tutorial/static/js/site.js','utf8');
for(const unavailableStorage of [false,true])test('menu works without jQuery; unavailable storage='+unavailableStorage,()=>{
 const classes=new Set(),events={},attrs={},sidebar={hidden:false},store=new Map();
 const button={setAttribute:(k,v)=>attrs[k]=v,querySelector:()=>null};
 const document={readyState:'complete',body:{classList:{contains:k=>classes.has(k),toggle(k,force){const on=force===undefined?!classes.has(k):force;on?classes.add(k):classes.delete(k);return on;}}},querySelector:()=>sidebar,querySelectorAll:()=>[button],addEventListener:(k,f)=>events[k]=f};
 const localStorage={getItem(k){if(unavailableStorage)throw Error('storage disabled');return store.get(k);},setItem(k,v){if(unavailableStorage)throw Error('storage disabled');store.set(k,v);}};
 const window={dispatchEvent(){}};
 vm.runInNewContext(source,{document,window,localStorage,Event:class{}});
 assert.equal(sidebar.hidden,false);
 const event={target:{closest:()=>button},preventDefault(){}};
 events.click(event);assert.equal(sidebar.hidden,true);assert.equal(attrs['aria-expanded'],'false');
 events.click(event);assert.equal(sidebar.hidden,false);assert.equal(attrs['aria-expanded'],'true');
});
