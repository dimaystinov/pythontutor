const {test}=require('node:test'),assert=require('node:assert/strict');
const {start,LIMIT}=require('./ui/session.js');
function fixture(last=0){let now=last,logout=0,touches=0,deadline;const events={};const data=new Map([['tutor-native-profile','profile']]);
 const storage={getItem:k=>data.get(k)??null,setItem:(k,v)=>data.set(k,String(v)),removeItem:k=>data.delete(k)};
 const options={id:'a',storage,now:()=>now,setTimeout:(f,ms)=>{deadline={f,ms};return 1;},clearTimeout(){},on:(k,f)=>events[k]=f,touch:()=>{touches++;return Promise.resolve();},logout:()=>{logout++;},};
 start(options);return {events,storage,options,time:t=>now=t,expired:()=>logout,deadline:()=>deadline,touches:()=>touches};}
test('idle timeout logs out at ten minutes and preserves student data',()=>{const f=fixture();f.storage.setItem('problem-draft:a:apples','saved');f.time(LIMIT);f.deadline().f();assert.equal(f.expired(),1);assert.equal(f.storage.getItem('tutor-native-profile'),null);assert.equal(f.storage.getItem('problem-draft:a:apples'),'saved');});
test('typing and scrolling renew timer; focus after sleep does not',()=>{const f=fixture();f.time(500000);f.events.keydown();f.time(1099999);f.deadline().f();assert.equal(f.expired(),0);f.time(1100000);f.events.pageshow();assert.equal(f.expired(),1);});
test('navigation keeps the existing activity deadline',()=>{const f=fixture();f.time(500000);start(f.options);f.time(LIMIT);f.events.visibilitychange();assert.equal(f.expired(),1);});
test('activity after expiry cannot revive a session',()=>{const f=fixture();f.time(LIMIT+1);f.events.pointerdown();assert.equal(f.expired(),1);assert.equal(f.touches(),0);});
