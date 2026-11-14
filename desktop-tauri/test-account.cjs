const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
function app(failure){const nodes={},calls=[],data=new Map();for(const id of ['student-fields','legacy-fields','submit','student-title','login-mode','register-mode','legacy-mode','status','old-pin','pin','surname','given-name','account','legacy-name','legacy-password','school-class','autostart'])nodes[id]={value:'',classList:{toggle(){}},addEventListener(e,f){this[e]=f;},focus(){}};
 nodes.surname.value='ИВАНОВ';nodes['given-name'].value='Иван';nodes['school-class'].value='5';nodes.pin.value='password 123';
 const location={};vm.runInNewContext(fs.readFileSync(__dirname+'/ui/account.js','utf8'),{window:{__TAURI__:{core:{invoke:async(name,args)=>{calls.push({name,args});if(failure)throw Error(failure);return{id:'same-id',name:'Иванов Иван'};}}}},document:{getElementById:id=>nodes[id]},sessionStorage:{setItem:(k,v)=>data.set(k,v)},location,console,Date});
 return{nodes,calls,data,location,submit:()=>nodes.account.onsubmit({preventDefault(){}})};
}
test('student login passes password unchanged and class as number',async()=>{const f=app();await f.submit();assert.equal(f.calls[0].name,'enter_course');assert.equal(f.calls[0].args.password,'password 123');assert.equal(f.calls[0].args.schoolClass,5);assert.equal(f.location.href,'/pythontutor/');assert.ok(f.data.has('tutor-last-activity:same-id'));});
test('short password never invokes native login',async()=>{const f=app();f.nodes.pin.value='123';await f.submit();assert.equal(f.calls.length,0);assert.match(f.nodes.status.textContent,/8 символов/);});
test('old profile migrates with its original ID before entering course',async()=>{const f=app();f.nodes['legacy-mode'].onclick();await f.submit();assert.equal(f.calls[0].name,'login');assert.equal(f.location.href,undefined);assert.equal(f.nodes['legacy-fields'].disabled,true);f.nodes.pin.value='password 456';await f.submit();assert.equal(f.calls[1].name,'enter_course');assert.equal(f.calls[1].args.legacy,'same-id');assert.equal(f.location.href,'/pythontutor/');});

test('rejected password stays on login without session, autostart or navigation',async()=>{
 const f=app('Неверный пароль.');await f.submit();
 assert.equal(f.calls.length,1);assert.equal(f.location.href,undefined);assert.equal(f.data.size,0);
 assert.equal(f.nodes.status.textContent,'Неверный пароль.');assert.equal(f.nodes.submit.disabled,false);
});
