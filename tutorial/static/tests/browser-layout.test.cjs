const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
// querySelector on a selector list returns the first element in document order:
// .main precedes its child #visualizer. A status must not become a grid column.
let ready, placement;
const main={before:()=>placement='outside',prepend:()=>placement='inside'};
const editor={before:()=>placement='inside'};
vm.runInNewContext(fs.readFileSync('tutorial/static/js/browser-execution.js','utf8'),{window:{},document:{
 querySelector(s){if(s.startsWith('meta'))return {content:'browser'};if(s.includes('.main'))return main;return editor;},
 querySelectorAll(){return [];},createElement(){return {dataset:{},setAttribute(){}};},
 addEventListener(_,f){ready=f;}
}});
ready();assert.equal(placement,'inside','Python status must stay inside the task column');
console.log('PASS browser status keeps the task inside the layout');
