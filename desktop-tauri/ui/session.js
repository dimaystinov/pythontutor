(function(root){
'use strict';
const LIMIT=10*60*1000;
function start({id,storage,now=Date.now,setTimeout,clearTimeout,on,touch,logout}){
 const key='tutor-last-activity:'+id;
 let last=Number(storage.getItem(key)),timer,ended=false;
 if(storage.getItem(key)===null||!Number.isFinite(last)){last=now();storage.setItem(key,last);}
 function end(){if(ended)return;ended=true;clearTimeout(timer);storage.removeItem('tutor-native-profile');storage.removeItem(key);logout();}
 function check(){if(ended)return;if(now()-last>=LIMIT||now()<last){end();return;}clearTimeout(timer);timer=setTimeout(check,LIMIT-(now()-last));}
 function activity(){if(ended)return;if(now()-last>=LIMIT||now()<last){end();return;}last=now();storage.setItem(key,last);check();Promise.resolve(touch()).catch(end);}
 for(const event of ['pointerdown','keydown','wheel','touchstart'])on(event,activity);
 for(const event of ['pageshow','visibilitychange','focus'])on(event,check);
 check();return {check};
}
const api={start,LIMIT};if(typeof module==='object'&&module.exports)module.exports=api;else root.TutorSession=api;
})(typeof window==='undefined'?globalThis:window);
