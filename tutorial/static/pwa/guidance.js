/* Reviewed lesson hints: available without a model or network. */
(function(){
'use strict';
function next(text,turns,hints){
 if(!Array.isArray(hints)||hints.length!==2||!hints.every(h=>typeof h.text==='string'&&h.text.trim()))return null;
 const request=text.toLowerCase().trim().replace(/[.!?]+$/,'');
 if(!/^(?:дай(?:те)?(?: небольшую| ещё одну| еще одну)? подсказку(?:, с чего начать\. не выдавай решение целиком)?|подсказка|ещ[её](?: одну)? подсказку|следующая подсказка|с чего начать(?: решение)?|покажи (?:первую|вторую) подсказку)$/.test(request))return null;
 const previous=turns.reduce((n,t)=>Math.max(n,Number(t.guidedHint)||0),0);
 const index=request.includes('первую')?1:request.includes('вторую')?2:Math.min(previous+1,3);
 if(index===3)return {guidedHint:3,answer:'Обе подсказки уже показаны. Попробуй применить их к маленькому примеру из условия. Если застрянешь, напиши, какой именно шаг непонятен.'};
 const hint=hints[index-1];
 return {guidedHint:index,answer:'Подсказка '+index+' из 2.\n\n'+hint.text+(hint.example?'\n\nПример отдельного действия:\n```python\n'+hint.example+'\n```':'')};
}
function diagnose(code,run){
 if(!code.trim())return 'Редактор пока пуст. Начни с первой подсказки: определи, какие данные нужно прочитать.';
 if(!run)return 'Сначала нажми «запустить» или «Проверить решение на всех тестах». Я смогу объяснить результат запуска, а не угадывать ошибку по коду.';
 if(run.code!==code)return 'Ты изменил код после последнего запуска. Запусти его ещё раз, чтобы мы разбирали актуальную ошибку.';
 if(run.result==='ok')return run.checked?'Проверка пройдена: '+run.total+' из '+run.total+' тестов. Попробуй своими словами объяснить, что делает каждая строка. Затем можно перейти к следующей задаче.':'Этот запуск завершился без ошибки Python. Это ещё не проверка правильности решения: нажми «Проверить решение на всех тестах».';
 const ex=run.exception||{},type=ex.exception_type||'';
 const explanations={
  NameError:'Python не знает это имя. Проверь написание переменной и убедись, что ей присвоено значение до использования.',
  UnboundLocalError:'В этой ветке выполнения переменная ещё не получила значение. Проверь, где она создаётся до использования.',
  ValueError:'Значение не подходит для выбранной операции. Например, int() ожидает запись целого числа. Сравни входные данные с тем, как ты их читаешь.',
  TypeError:'Операция получила неподходящий тип данных. Помни: input() возвращает строку. Проверь типы значений в указанной строке.',
  ZeroDivisionError:'В делении или остатке от деления делитель оказался равен нулю. Проследи, откуда он получается.',
  IndexError:'Индекс вышел за границы строки или списка. Первый индекс — 0, последний — длина минус 1.',
  KeyError:'В словаре нет указанного ключа. Проверь, какие ключи были добавлены до этого обращения.',
  EOFError:'Программа попросила больше входных данных, чем было передано. Сравни вызовы input() с количеством строк во входных данных.',
  IndentationError:'Python не понял отступы. Строки одного блока должны иметь одинаковый отступ; после условия или цикла нужен вложенный блок.',
  TabError:'В отступах смешаны табуляции и пробелы. Используй один способ, обычно четыре пробела.',
  SyntaxError:'Python не смог прочитать запись программы. Проверь скобки, кавычки и двоеточия; причина может быть и в предыдущей строке.',
  RecursionError:'Слишком много вложенных вызовов функции. Проверь условие остановки рекурсии и приближается ли каждый вызов к нему.'
 };
 let advice=explanations[type];
 if(!advice&&['realtime_limited','instructions_limited'].includes(run.result))advice='Программа достигла лимита выполнения. Проверь, меняются ли переменные в цикле и может ли условие цикла стать ложным.';
 if(!advice&&run.result==='output_limited')advice='Программа вывела слишком много текста. Проверь print() внутри циклов и условие завершения цикла.';
 if(!advice&&run.result==='invalid_image')advice='Проверка не получила допустимое изображение output.png. Проверь имя файла, сохранение результата и ограничение размера.';
 if(!advice&&run.result==='wrong_answer'){
  advice='Программа выполнилась, но результат не совпал с ожидаемым.';
  if(run.expected!==null&&run.expected!==undefined)advice+='\n\nВходные данные:\n```text\n'+run.stdin+'\n```\nТвой вывод:\n```text\n'+(run.stdout?.trim()?run.stdout:'(пусто)')+'\n```\nОжидается:\n```text\n'+run.expected+'\n```';
  else advice+=' Сравни полученное изображение с требованиями задачи.';
  advice+='\n\nПроследи значения переменных на этом примере по шагам. При необходимости включи пошаговое выполнение.';
 }
 if(!advice)advice='Запуск завершился с ошибкой. Посмотри сообщение Python ниже и проверь указанную операцию; точную причину без дополнительного разбора я не утверждаю.';
 const line=Number(ex.line);
 return (run.checked&&run.test?'Первый непройденный тест: '+run.test+'. Пройдено '+run.passed+' из '+run.total+'.\n\n':'')+(type?type+(Number.isInteger(line)&&line>0?' · строка '+line:'')+'\n\n':'')+advice+(ex.exception_msg?'\n\nСообщение Python: '+String(ex.exception_msg).slice(0,500):'')+'\n\nИсправь один шаг и запусти проверку снова.';
}
function review(text,code,run,allowed=true){
 if(!/^(?:Посмотри мой текущий код: помоги найти ошибку и понять её причину\.|проверь мой код[.!?]?|почему ошибка[.!?]?|объясни ошибку[.!?]?)$/i.test(text.trim()))return null;
 return {answer:allowed?diagnose(code,run):'Доступ к коду отключён в настройках помощника. Включи его, чтобы разобрать результат запуска.'};
}
function current(text,turns){
 const source=document.getElementById('tutor-hints-data');
 try{return next(text,turns,JSON.parse(source?.textContent||'null'));}catch(_){return null;}
}
window.TutorGuidance={next,current,review,diagnose};
})();
