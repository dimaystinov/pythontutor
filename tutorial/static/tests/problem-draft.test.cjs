const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');

const source = fs.readFileSync(path.join(__dirname, '../js/problem.js'), 'utf8');
const storage = new Map();
const reads = [];
const writes = [];
const draft = code => JSON.stringify({solution: {code, stdin: '1\n2'}});
storage.set('problem[aplusb]', draft('legacy secret'));

// Exercise the actual page initialization and autosave callback with shared
// browser storage. Each login receives its own server-rendered user attribute.
function openPage(userId, problem = 'aplusb') {
    let autosave;
    let editor;
    let change;
    let notifications = 0;
    const element = {
        text: () => 'server draft',
        attr: name => name === 'data-draft-user-id' ? userId : undefined,
        toggle() {},
        click() {},
    };
    function $(selector) {
        if (typeof selector === 'function') selector();
        return element;
    }
    function Visualizer(selector, code, stdin) {
        this.code = code === undefined ? 'server draft' : code;
        this.stdin = stdin;
        this.focusCodeEditor = () => {};
        this.on = (event, handler) => { if (event === 'change_code') change = handler; };
        editor = this;
    }
    const context = vm.createContext({
        $, Visualizer, problem_name: problem,
        Event: class { constructor(type) { this.type = type; } },
        window: {addEventListener() {}, dispatchEvent() { notifications++; }},
        localStorage: {
            getItem(key) { reads.push(key); return storage.get(key) ?? null; },
            setItem(key, value) { writes.push(key); storage.set(key, value); },
        },
        setInterval(callback) { autosave = callback; },
    });
    vm.runInContext(source, context);
    return {editor, save: () => autosave(), change: () => change(), notifications: () => notifications};
}

const first = openPage('101');
assert.equal(first.editor.code, 'server draft', 'Legacy drafts must not be imported');
first.editor.code = 'first user secret';
first.save();
const firstKey = writes.at(-1);
assert.equal(openPage('101').editor.code, 'first user secret', 'Owner restores their draft');

const second = openPage('202');
assert.equal(second.editor.code, 'server draft', 'Another user must not load the first draft');
second.editor.code = 'second user draft';
second.save();
assert.notEqual(writes.at(-1), firstKey, 'Users must write distinct keys');
assert.equal(openPage('101').editor.code, 'first user secret', 'Other autosaves must not overwrite owner draft');
assert.equal(openPage('101', 'another_task').editor.code, 'server draft', 'Tasks must have distinct drafts');
assert.ok(!reads.includes('problem[aplusb]'), 'Never read the legacy shared key');

const anonymous = openPage('');
assert.equal(anonymous.editor.code,'server draft','Local profile does not read signed-in drafts');
anonymous.editor.code='offline draft';anonymous.save();
assert.ok(writes.at(-1).startsWith('problem-draft:local:'),'Offline drafts have a separate namespace');
assert.equal(openPage('').editor.code,'offline draft','Offline draft survives reload');
assert.equal(openPage('101').editor.code,'first user secret','Offline writes never overwrite account drafts');
console.log('Problem drafts isolate users, local profile and tasks.');

const untouched = openPage('fresh');
untouched.save();
assert.equal(JSON.parse(storage.get('problem-draft:fresh:aplusb')).started, false);
assert.equal(JSON.parse(storage.get('problem-draft:fresh:aplusb')).started, false);
const reopened = openPage('fresh');
assert.equal(JSON.parse(storage.get('problem-draft:fresh:aplusb')).started, false, 'Viewing the starter twice does not mark a task as started');
reopened.editor.code = 'print(0)';
reopened.change();
assert.equal(JSON.parse(storage.get('problem-draft:fresh:aplusb')).started, true);
assert.equal(reopened.notifications(), 1, 'First edit updates menu immediately');
openPage('fresh');
assert.equal(JSON.parse(storage.get('problem-draft:fresh:aplusb')).started, true, 'Started state survives reload');
console.log('Untouched starters remain neutral; real edits persist started state.');
