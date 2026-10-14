// Run with node tutorial/static/tests/visualizer-security.test.cjs.
// Exercise the actual legacy rendering function with a minimal DOM sink double.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../js/visualizer.js'), 'utf8');
const start = source.indexOf('function renderData(obj, elem) {');
const end = source.indexOf('\n\t\tplumb.repaintEverything()', start);
const renderSource = source.slice(start, end);
const textValues = [];
const markupValues = [];
class Element {
    text(value) { textValues.push(String(value)); return this; }
    append(value) { if (typeof value === 'string') markupValues.push(value); return this; }
    find() { return new Element(); }
    children() { return new Element(); }
}
function $(value) {
    if (typeof value === 'string') markupValues.push(value);
    return value instanceof Element ? value : new Element();
}
$.isArray = Array.isArray;
const context = vm.createContext({ $, assert, getObjectID: obj => obj[0] === 'INSTANCE' || obj[0] === 'CLASS' ? obj[2] : obj[1] });
vm.runInContext(renderSource, context);
const payload = '<img src=x onerror="globalThis.injected=true">';
for (const value of [payload, ['INSTANCE', payload, 1], ['CLASS', payload, 2, [payload]], [payload, 3, '<custom at 0x123>'], [payload, 4, 'custom repr'], ['CIRCULAR_REF', payload]]) {
    textValues.length = 0;
    markupValues.length = 0;
    context.renderData(value, new Element());
    assert(textValues.some(value => value.includes('<img src=x')), 'learner text remains visible');
    assert(!markupValues.some(value => value.includes('<img src=x')), 'learner text never reaches an HTML sink');
}
assert(source.indexOf("server_res.result === 'output_limited'") < source.indexOf('_explain(server_res);'), 'output limit handled before trace rendering');
console.log('Visualizer unsafe-label regression checks passed.');
