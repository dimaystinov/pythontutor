const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const context=vm.createContext({window:{}});
vm.runInContext(fs.readFileSync('tutorial/static/pwa/local-ai.js','utf8'),context);
const {hintOnly,choices}=context.window.TutorLocalAI;
const full='Вы складываете строку с числом. Как проверить тип? Вот исправленный код:\n```python\nprint(int(input())+1)\n```';
assert.equal(hintOnly(full,false),'Вы складываете строку с числом. Как проверить тип?');
assert.equal(hintOnly(full,true),full,'After success full explanation and code remain available');
assert.ok(!hintOnly('```python\nprint(42)\n```',false).includes('print'));
assert.equal(choices.length,1);
assert.ok(!choices.some(m=>/Coder-(0\.5|1\.5)B/.test(m.id)));
assert.equal(choices[0].id,'Qwen2.5-Coder-7B-Instruct-q4f16_1-MLC');
console.log('PASS local hints hide ready code until success; solved explanations preserved');
const conversational='Привет! Я помогу разобраться. Можно начать с условия. Потом посмотрим твой код.';
assert.equal(hintOnly(conversational,false),conversational,'Normal conversation must not be cut to two sentences');
const messages=context.window.TutorLocalAI.dialogueMessages('Qwen2.5-Coder-7B-Instruct-q4f16_1-MLC',{question:'А почему?',code:'print(1)',context:'Урок',turns:[{question:'Что такое int?',answer:'Преобразование в целое число.'}],solved:false});
assert.equal(messages.at(-1).content,'А почему?','Latest question must be the actual user message');
assert.ok(messages.some(m=>m.role==='assistant'&&m.content.includes('Преобразование')),'Preserve dialogue context');
assert.ok(messages[0].content.includes('print(1)'),'Editor is background, not the latest question');
console.log('PASS conversational context and complete natural answers');

assert.equal(messages.filter(m=>m.role==='system').length,1,'WebLLM accepts system only at index zero');
const taskMessages=context.window.TutorLocalAI.dialogueMessages('qwen',{question:'Объясни условие простыми словами',context:'Задача «Площадь прямоугольного треугольника». Считайте длины двух катетов. Выведите площадь.',turns:[{question:'Помоги',answer:'Какую задачу?'}]});
assert.ok(taskMessages[0].content.includes('Считайте длины двух катетов'));
assert.ok(taskMessages[0].content.includes('Не проси назвать задачу повторно'));
assert.equal(taskMessages.at(-1).content,'Объясни условие простыми словами');
console.log('PASS current statement accompanies follow-up questions despite stale chat history');

const longStatement='Условие '.repeat(320)+' В конце выведите число ошибок.';
const complete=context.window.TutorLocalAI.dialogueMessages('qwen',{question:'Что вывести?',context:longStatement,turns:[]});
assert.ok(complete[0].content.includes('В конце выведите число ошибок.'),'Keep the full longest current task statement');

assert.ok(!hintOnly('Проверь это:\n```python\nprint(42)\n```',false).endsWith('это:'),'No empty lead-in when ready code is removed');
assert.ok(messages[0].content.includes('5 / 2 == 2.5'));

assert.equal(hintOnly('input возвращает строку.\nИсправленный код будет выглядеть так:\n```python\nprint(42)\n```',false),'input возвращает строку.');

const drawing='Прямоугольник:\n```text\n+---+\n| / |\n+---+\n```\nДиагональ делит его на две равные части.';
assert.equal(hintOnly(drawing,false),drawing,'Keep diagrams and the explanation after them');
