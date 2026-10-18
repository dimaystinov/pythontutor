const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const ctx={window:{},document:{getElementById:()=>null}};vm.runInNewContext(fs.readFileSync('tutorial/static/pwa/guidance.js','utf8'),ctx);
const next=ctx.window.TutorGuidance.next,hints=[{text:'Считай два катета.'},{text:'S = a × b / 2. Деление / сохраняет дробную часть.'}];
const first=next('Дай небольшую подсказку, с чего начать. Не выдавай решение целиком.',[],hints);assert.equal(first.guidedHint,1);assert.ok(first.answer.includes(hints[0].text));
const second=next('Дай подсказку',[first],hints);assert.equal(second.guidedHint,2);assert.ok(second.answer.includes('a × b / 2'));
assert.equal(next('Ещё подсказку',[first,second],hints).guidedHint,3);
assert.equal(next('Покажи первую подсказку',[first,second],hints).guidedHint,1);
assert.equal(next('Почему input возвращает строку?',[],hints),null);
assert.equal(next('Дай подсказку',[],[]),null);
assert.equal(next('Дай подсказку',[],hints).guidedHint,1);
console.log('PASS reviewed hints in order, explicit replay, no model required, other questions remain conversational');
const {diagnose,review}=ctx.window.TutorGuidance;
const code='print(a)';
const failure={code,result:'unhandled_exception',exception:{exception_type:'NameError',exception_msg:"name 'a' is not defined",line:1}};
assert.match(diagnose(code,failure),/Python не знает это имя/);
assert.match(diagnose(code,failure),/строка 1/);
assert.match(diagnose('print(1)',failure),/изменил код/);
assert.match(diagnose(code,null),/Сначала нажми/);
assert.match(diagnose('',failure),/Редактор пока пуст/);
assert.match(diagnose(code,{code,result:'ok',checked:false}),/ещё не проверка/);
assert.match(diagnose(code,{code,result:'ok',checked:true,total:4}),/Проверка пройдена: 4 из 4/);
assert.match(diagnose(code,{code,result:'wrong_answer',checked:true,test:2,passed:3,total:4,stdin:'3\n5',stdout:'7\n',expected:'7.5'}),/Ожидается:\n```text\n7.5/);
assert.match(diagnose(code,{code,result:'wrong_answer',expected:null}),/изображение/);
assert.match(diagnose(code,{code,result:'realtime_limited'}),/лимита выполнения/);
assert.match(review('Проверь мой код',code,failure,false).answer,/Доступ к коду отключён/);
assert.equal(review('Привет',code,failure),null);
for(const type of ['SyntaxError','TypeError','ValueError','EOFError','IndexError','KeyError','ZeroDivisionError','RecursionError','TabError','IndentationError']){
 const answer=diagnose(code,{...failure,exception:{exception_type:type,line:1}});
 assert.ok(!answer.includes('точную причину без дополнительного разбора'),type);
}
console.log('PASS execution-based explanations, outdated-code guard, code privacy, limits, wrong answers and successful runs');

const consult=ctx.window.TutorGuidance.consult;
assert.match(consult('Забыл поставить двоеточие', {code:'if x > 0',run:{code:'if x > 0',result:'unhandled_exception',exception:{exception_type:'SyntaxError',exception_msg:"expected ':'",line:1}}}).answer,/двоеточие/);
assert.match(consult('Объясни условие простыми словами', {material:'Считать два катета и найти площадь'}).answer,/два катета/);
assert.match(consult('Почему тест 2 не прошёл?',{code,run:{code,checked:true,total:2,passed:1,tests:[{result:'ok'},{result:'wrong_answer',stdout:'YES',expected:'NO',stdin:'4'}]}}).answer,/NO/);
assert.match(consult('Проверь мой код',{code:'changed',run:failure}).answer,/изменил код/);
assert.match(consult('Почему ошибка?',{code,run:failure,allowed:false}).answer,/Доступ к коду отключён/);
assert.match(consult('Что такое range?').answer,/правая граница/);
assert.match(consult('Придумай роман').answer,/заготовки/);
assert.match(diagnose('print()', {code:'print()',result:'wrong_answer',stdout:'',expected:'3'}),/Вывод пуст/);
assert.match(diagnose('print()', {code:'print()',result:'wrong_answer',stdout:'yes',expected:'YES'}),/регистр/);
console.log('PASS deterministic dialogue, specific test context, missing colon, output comparison, privacy, stale code and honest fallback');

for(const [type,msg,expected] of [['SyntaxError',"'break' outside loop",/внутри `for`/],['SyntaxError',"'return' outside function",/внутри функции/],['TypeError',"'NoneType' object is not iterable",/возвращает ли функция/]]){assert.match(diagnose(code,{code,result:'unhandled_exception',exception:{exception_type:type,exception_msg:msg}}),expected);}
