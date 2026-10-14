const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
let worker,reset;class Worker {constructor(){worker=this;}postMessage(){}terminate(){}}
const window={addEventListener:(name,fn)=>{reset=fn;}};
vm.runInNewContext(fs.readFileSync('tutorial/static/js/browser-execution.js','utf8'),{window,Worker,setTimeout,clearTimeout,document:{querySelector:()=>({content:'browser'}),querySelectorAll:()=>[],addEventListener:()=>{}}});
(async()=>{
 const job={code:'print(7)',tests:[{stdin:'3\n5',answer:'7.5'},{stdin:'2\n2',answer:'2'}]};
 const pending=window.BrowserPython.run(job);await Promise.resolve();
 worker.onmessage({data:{result:[{result:'wrong_answer',stdout:'7'},{result:'ok',stdout:'2'}]}});await pending;
 const report=window.BrowserPython.lastRun();assert.equal(report.test,1);assert.equal(report.expected,'7.5');assert.equal(report.passed,1);assert.equal(report.code,job.code);assert.equal(report.stdin,'3\n5');
 reset({key:"tutor-progress-reset:local"});assert.equal(window.BrowserPython.lastRun(),null);
 console.log('PASS actual worker result is available to assistant and reset clears it');
})().catch(e=>{console.error(e);process.exitCode=1;});
