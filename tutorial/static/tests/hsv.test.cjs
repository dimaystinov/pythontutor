const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync('tutorial/static/hsv/index.html','utf8');
const conversion=html.slice(html.indexOf('    function roundEven'),html.indexOf('    function drawLabel'));
const components=html.slice(html.indexOf('    function findComponents'),html.indexOf('    function render'));
const sandbox={state:{areaMin:1,areaMax:10}};vm.createContext(sandbox);vm.runInContext(conversion+components,sandbox);
for(const [rgb,hsv] of [[[255,0,0],[0,255,255]],[[0,255,0],[60,255,255]],[[0,0,255],[120,255,255]],[[255,255,255],[0,0,255]],[[0,0,0],[0,0,0]]])assert.deepEqual(Array.from(sandbox.hsvFromRgb(...rgb)),hsv);
assert.equal(sandbox.findComponents(new Uint8Array([1,0,0,1]),2,2).length,1);
sandbox.state.areaMin=3;assert.equal(sandbox.findComponents(new Uint8Array([1,0,0,1]),2,2).length,0);
console.log('PASS OpenCV HSV reference colors, 8-connected components, area filter');
if(process.env.HSV_FIXTURE){let seed=12345;const random=()=>{seed=(seed*1664525+1013904223)>>>0;return seed>>>24;};const rows=Array.from({length:10000},()=>{const rgb=[random(),random(),random()];return {rgb,hsv:Array.from(sandbox.hsvFromRgb(...rgb))};});fs.writeFileSync(process.env.HSV_FIXTURE,JSON.stringify(rows));}
