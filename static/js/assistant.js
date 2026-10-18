(function () {
    'use strict';
    const panel=document.getElementById('tutor-panel');
    if(!panel) return;
    const $=id=>document.getElementById(id), launcher=$('tutor-launcher');
    let loaded=false,busy=false,voiceMode=false,callActive=false,recording=null,audio=null,audioFinish=null,epoch=0,voiceReady=false;
    let lastCode='',pending=null;
    const workspace=$('tutor-workspace'),divider=$('tutor-divider');
    const question=$('tutor-question'),log=$('tutor-messages'),status=$('tutor-status');
    const model=$('tutor-model');
    try {
        // One-time migration: existing learners also start with the no-download tutor.
        if(model&&localStorage.getItem('tutor-guided-default-v1')!=='1'){
            localStorage.setItem('tutor-ai-model','guided');
            localStorage.setItem('tutor-guided-default-v1','1');
        }
        const choice=localStorage.getItem('tutor-ai-model');
        if(choice&&model?.querySelector('option[value="'+choice.replace(/[^\w.-]/g,'')+'"]'))model.value=choice;
        else if(!choice&&model)model.value='guided';
        else if(model&&choice){model.value='guided';localStorage.setItem('tutor-ai-model',model.value);}
    } catch(_){}
    const guided=()=>model?.value==='guided';
    const api=()=>model?.value==='opencode-local';
    const local=()=>!!model&&model.value!=='cloud';
    const chatStore=window.TutorChatHistory.create(localStorage,window.TutorDevice.owner());
    let localTurns=[],modelPromise=null,mathQueue=Promise.resolve();
    function friendlyProgress(text){
        const percent=String(text).match(/Загрузка модели: (\d+)%/);
        const label=percent?'Готовлю помощника · '+percent[1]+'%':String(text).includes('Модель готова')?'Готов к разговору':String(text).includes('Подготовка модели')?'Готовлю помощника…':text;
        notice(label);if(voiceMode)voiceStatus(label);
    }
    window.addEventListener('tutor-model-needed',event=>{
        const setup=$('tutor-model-setup');
        if(setup)window.TutorModelAssets.mount(setup,event.detail,()=>event.detail==='qwen7b'?prepareModel():window.TutorLocalVoice.prepare(friendlyProgress)).catch(e=>notice(e.message,true));
    });
    function prepareModel(){
        if(!local()||guided())return Promise.resolve();
        if(!modelPromise){model.disabled=true;modelPromise=window.TutorLocalAI.load(model.value,friendlyProgress).finally(()=>{modelPromise=null;model.disabled=busy;});}
        return modelPromise;
    }
    function localHistory(){try{localTurns=chatStore.list();}catch(_){localTurns=[];}return localTurns;}
    function taskHistory(){return localHistory().filter(t=>!t.task||t.task===panel.dataset.url);}
    function saveTurn(result){try{localTurns=chatStore.append(result,panel.dataset.url);}catch(_){notice('Не удалось сохранить переписку: недостаточно места на устройстве.',true);}}
    function describeModel(){if($('tutor-privacy'))$('tutor-privacy').textContent=guided()?'Встроенный консультант использует правила и заготовленные объяснения. Код и вопросы остаются на устройстве.':'Qwen обрабатывает код на устройстве. OpenCode отправляет вопрос, условие и разрешённый код облачному провайдеру. ИИ может ошибаться.';if($('tutor-api-settings'))$('tutor-api-settings').hidden=!api();const c=window.TutorLocalAI?.choices.find(c=>c.id===model?.value);if($('tutor-model-info'))$('tutor-model-info').textContent=c?c.download+' загрузка, '+c.memory+'. '+c.note:guided()?'Объясняет ошибки и тесты по правилам. Не требует загрузок и интернета.':'Обработка через настроенный API. Нужен интернет.';if($('tutor-load-model'))$('tutor-load-model').hidden=!c;if($('tutor-load-voice'))$('tutor-load-voice').hidden=!c;}
    let pairingWindow;
    $('tutor-connect-desktop')?.addEventListener('click',()=>{
        if(location.origin==='http://127.0.0.1:8043'){prepareModel().then(()=>{$('tutor-desktop-status').textContent='Приложение подключено.';}).catch(e=>notice(e.message,true));return;}
        pairingWindow=window.open('http://127.0.0.1:8043/connect','pythontutor-connect','width=600,height=350');
        $('tutor-desktop-status').textContent=pairingWindow?'Подтвердите подключение в открывшемся окне.':'Браузер не открыл окно. Разрешите всплывающее окно или вставьте код из приложения.';
    });
    window.addEventListener('message',event=>{
        if(event.origin!=='http://127.0.0.1:8043'||!pairingWindow||event.source!==pairingWindow||event.data?.type!=='pythontutor-pair'||typeof event.data.token!=='string')return;
        $('tutor-api-key').value=event.data.token;$('tutor-desktop-status').textContent='Приложение подключено.';
    });
    describeModel();
    const csrf=()=>panel.querySelector('[name=csrfmiddlewaretoken]').value;
    function notice(text,error=false){if(status){status.textContent=text;status.classList.toggle('error',error);}}
    function codeNow(){
        if(panel.dataset.kind==='problem' && window.visualizer) return String(window.visualizer.code||'');
        if(panel.dataset.kind==='image' && window.ace && document.getElementById('image-code')) return window.ace.edit('image-code').getValue();
        return '';
    }
    function updateCode(){
        if(!$('tutor-include-code')) return;
        const code=codeNow();lastCode=code;
        if(panel.dataset.kind==='lesson'){$('tutor-include-code').checked=false;panel.querySelector('.tutor-code-access').hidden=true;return;}
        $('tutor-code-status').textContent=$('tutor-include-code').checked ? (code.trim()?`Актуальный код · ${code.split('\n').length} строк · отправится с вопросом`:'Редактор пока пуст'):'Доступ к коду отключён';
    }
    async function request(url,data){
        const options=data?{method:'POST',body:data,headers:{'X-CSRFToken':csrf()}}:{};
        const response=await fetch(url,{...options,credentials:'same-origin'});
        if(response.redirected) throw new Error('Сеанс завершён. Войдите снова.');
        const type=response.headers.get('content-type')||'';
        if(!response.ok){let message='Не удалось обратиться к помощнику. Попробуйте снова.';if(type.includes('json')){const body=await response.json();message=body.error||message;}throw new Error(message);}
        return type.includes('json')?response.json():response.blob();
    }
    function formatted(node,text){
        const parts=text.split(/(```[\s\S]*?```)/g);
        for(const part of parts){
            if(part.startsWith('```')&&part.endsWith('```')){const pre=document.createElement('pre'),code=document.createElement('code');code.textContent=part.slice(3,-3).replace(/^[\w+-]*\n/,'');pre.append(code);node.append(pre);}
            else {for(const token of part.split(/(\*\*[^*\n]+\*\*|`[^`\n]+`)/g)){const el=document.createElement(token.startsWith('**')&&token.endsWith('**')?'strong':token.startsWith('`')&&token.endsWith('`')?'code':'span');el.textContent=el.tagName==='STRONG'?token.slice(2,-2):el.tagName==='CODE'?token.slice(1,-1):token;node.append(el);}}
        }
    }
    function typesetMessage(node){
        // Model text is untrusted: never allow links, HTML styling or TeX macros.
        if(/\\(?:href|url|style|class|cssId|html|includegraphics|require|def|gdef|edef|xdef|let|csname|newcommand|renewcommand|newenvironment|renewenvironment)\b/i.test(node.textContent))return;
        const math=window.MathJax;
        if(!math?.typesetPromise){window.addEventListener('load',()=>typesetMessage(node),{once:true});return;}
        mathQueue=mathQueue.then(()=>math.startup?.promise).then(()=>{
            if(node.isConnected)return math.typesetPromise([node]);
        }).then(()=>{log.scrollTop=log.scrollHeight;}).catch(()=>{});
    }
    async function copy(text){try{await navigator.clipboard.writeText(text);notice('Сообщение скопировано.');}catch(_){notice('Выделите текст сообщения и скопируйте его.',true);}}
    function message(role,text,id,theory){
        const item=document.createElement('div');item.className='tutor-message '+role;
        const body=document.createElement('div');body.className='message-body';formatted(body,text);item.append(body);
        if(role==='assistant'){
            const tools=document.createElement('div');tools.className='tutor-message-tools';
            const button=document.createElement('button');button.type='button';button.textContent='Копировать';button.addEventListener('click',()=>copy(text));tools.append(button);
            if(id&&voiceReady){const play=document.createElement('button');play.type='button';play.textContent='Слушать';play.addEventListener('click',async()=>{stopCall();try{await speak(id);}catch(e){notice(e.message,true);}});tools.append(play);}
            item.append(tools);
        }
        if(theory&&/^[a-z_]+$/.test(theory)){const link=document.createElement('a');link.href='/pythontutor/lessons/'+theory+'/';link.textContent='Открыть теорию';body.append(document.createElement('br'),link);}
        log.append(item);typesetMessage(body);log.scrollTop=log.scrollHeight;
    }
    async function history(){
        if(local()){
            log.querySelectorAll('.tutor-message').forEach(e=>e.remove());
            for(const turn of localHistory()){message('user',turn.question);message('assistant',turn.answer,null,turn.theory);}
            $('tutor-context').textContent=guided()?'Питоныч · встроенный консультант':api()?'Питоныч · OpenCode CLI':'Питоныч · локальный помощник';
            voiceReady=true;loaded=true;$('tutor-voice-mode').disabled=false;$('tutor-dictate').disabled=false;
            if(guided()){notice('Готов помочь с задачей.');return;}
            if(api()){notice('Помощник работает через приложение PythonTutor.');return;}
            prepareModel().catch(e=>notice(e.message||String(e),true));return;
        }
        notice('Загружаю историю…');
        try{
            const data=await request(panel.dataset.url);voiceReady=data.voice_available;
            $('tutor-context').textContent=data.title+(data.solved?' · задача решена':' · учимся шаг за шагом');
            log.querySelectorAll('.tutor-message').forEach(e=>e.remove());
            for(const turn of data.turns){message('user',turn.question);message('assistant',turn.answer,turn.id);}
            if(data.solved){const quick=panel.querySelector('[data-question]');quick.textContent='Как улучшить решение';quick.dataset.question='Я уже решил задачу. Сравни мой код с проверенным разбором и предложи улучшение с объяснением сложности.';}
            notice(data.configured?'':'ИИ пока не подключён администратором.',!data.configured);loaded=true;
            $('tutor-voice-mode').disabled=!voiceReady;$('tutor-dictate').disabled=!voiceReady;
        }catch(e){notice(e.message,true);}
    }
    let split=42;
    try { const saved=Number(localStorage.getItem('tutor-panel-width'));if(saved>=28&&saved<=60)split=saved; } catch(_) {}
    function layout(){
        const nav=document.querySelector('.navbar');
        document.documentElement.style.setProperty('--tutor-top',Math.max(0,nav?nav.getBoundingClientRect().bottom:0)+'px');
        workspace.style.setProperty('--tutor-width',split+'%');
        divider.setAttribute('aria-valuenow',String(Math.round(split)));
    }
    function resizeSplit(value){
        split=Math.max(28,Math.min(60,value));layout();
        try { localStorage.setItem('tutor-panel-width',String(split)); } catch(_) {}
        window.dispatchEvent(new Event('resize'));
    }
    divider.addEventListener('pointerdown',event=>{divider.setPointerCapture(event.pointerId);document.body.classList.add('tutor-resizing');});
    divider.addEventListener('pointermove',event=>{if(divider.hasPointerCapture(event.pointerId)){const rect=workspace.getBoundingClientRect();resizeSplit((rect.right-event.clientX)/rect.width*100);}});
    function endResize(){document.body.classList.remove('tutor-resizing');}
    divider.addEventListener('pointerup',event=>{divider.releasePointerCapture(event.pointerId);endResize();});
    divider.addEventListener('lostpointercapture',endResize);
    divider.addEventListener('keydown',event=>{if(['ArrowLeft','ArrowRight','Home'].includes(event.key)){event.preventDefault();resizeSplit(event.key==='Home'?42:split+(event.key==='ArrowLeft'?2:-2));}});
    window.addEventListener('resize',layout);
    layout();
    function setOpen(open){
        panel.hidden=!open;divider.hidden=!open;launcher.hidden=open;
        launcher.setAttribute('aria-expanded',String(open));document.body.classList.toggle('tutor-open',open);window.dispatchEvent(new Event('resize'));
        if(open){updateCode();if(question&&!loaded)history();if(question)question.focus();}
        else {stopCall();if(recording)finishRecording(false);launcher.focus();}
    }
    $('tutor-clear-chat')?.addEventListener('click',()=>{if(busy||callActive){notice('Сначала остановите ответ или голосовой разговор.',true);return;}$('tutor-clear-confirm').hidden=false;});
    $('tutor-clear-cancel')?.addEventListener('click',()=>{$('tutor-clear-confirm').hidden=true;});
    $('tutor-clear-accept')?.addEventListener('click',()=>{
        if(busy||callActive)return;
        if(window.TutorDevice.isCurrent&&!window.TutorDevice.isCurrent())return;
        try{chatStore.clear();localTurns=[];pending=null;log.querySelectorAll('.tutor-message').forEach(e=>e.remove());question.value='';$('tutor-clear-confirm').hidden=true;notice('Переписка удалена.');}catch(_){notice('Не удалось удалить переписку.',true);}
    });
    launcher.addEventListener('click',()=>setOpen(true));$('tutor-close').addEventListener('click',()=>setOpen(false));
    $('tutor-expand').addEventListener('click',()=>{const full=panel.classList.toggle('fullscreen');$('tutor-expand').setAttribute('aria-pressed',String(full));$('tutor-expand').setAttribute('aria-label',full?'Вернуть боковую панель':'Развернуть на весь экран');});
    document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!panel.hidden)setOpen(false);});
    // Each page starts with the launcher only; opening requires a user click.
    if(!question)return;
    model?.addEventListener('change',()=>{if(busy)return;stopCall();window.TutorLocalAI.stop();loaded=false;try{localStorage.setItem('tutor-ai-model',model.value);}catch(_){}describeModel();history();});
    $('tutor-prepare-ai')?.addEventListener('click',()=>prepareModel().catch(e=>notice(e.message||String(e),true)));
    window.addEventListener('storage',event=>{if(event.key==='tutor-ai-model'&&event.newValue==='guided'&&model){window.TutorLocalAI.stop();stopCall();model.value='guided';describeModel();notice('Компонент удалён. Включён встроенный консультант.');}});
    $('tutor-stop-model')?.addEventListener('click',()=>window.TutorLocalAI.stop());
    function setMode(voice){
        stopCall();
        if(voice)voiceStatus('Готовлю разговор…');
        voiceMode=voice;$('tutor-voice-view').hidden=!voice;log.hidden=voice;$('tutor-quick').hidden=voice;$('tutor-form').hidden=voice;
        $('tutor-text-mode').setAttribute('aria-pressed',String(!voice));$('tutor-voice-mode').setAttribute('aria-pressed',String(voice));
        if(voice)beginCall();
    }
    $('tutor-text-mode').addEventListener('click',()=>setMode(false));$('tutor-voice-mode').addEventListener('click',()=>setMode(true));
    $('tutor-include-code').addEventListener('change',updateCode);setInterval(()=>{if(!panel.hidden)updateCode();},600);
    function currentMaterial(){
        // Navigation and chat history must never displace the current statement.
        const material=document.querySelector('[data-tutor-material]');
        return material ? material.innerText.trim() : '';
    }
    async function send(text,fromVoice=false){
        if(busy)return null;text=text.trim();if(!text)return null;
        if(text.length>3000){notice('Сократите вопрос до 3000 символов.',true);return null;}
        const refusal=guided()?null:window.TutorLocalAI?.scopeRefusal(text);
        const prepared=guided()?window.TutorGuidance.consult(text,{code:codeNow(),run:window.BrowserPython?.lastRun?.(),allowed:!!$('tutor-include-code')?.checked,material:currentMaterial(),turns:taskHistory()}):refusal?{answer:refusal}:window.TutorGuidance?.current(text,taskHistory()) || window.TutorGuidance?.review(text,codeNow(),window.BrowserPython?.lastRun?.(),!!$('tutor-include-code')?.checked);
        if(prepared){
            if(window.TutorDevice.isCurrent&&!window.TutorDevice.isCurrent())return null;
            const result={question:text,...prepared,id:'local-'+crypto.randomUUID()};
            message('user',text);message('assistant',result.answer,result.id,result.theory);
            saveTurn(result);
            question.value='';notice('Помощь по задаче · работает без ИИ и интернета.');return result;
        }
        updateCode();const code=$('tutor-include-code').checked?lastCode:'';
        if(code.length>12000){notice('Код слишком длинный. Сократите его или отключите передачу кода.',true);return null;}
        if(!pending||pending.text!==text||pending.code!==code)pending={text,code,id:crypto.randomUUID()};
        busy=true;$('tutor-stop-model').hidden=false;$('tutor-send').disabled=true;notice('Питоныч думает…');
        const data=new FormData();data.set('question',text);data.set('code',code);data.set('request_id',pending.id);
        try{
            if(local()){
                await prepareModel();
                model.disabled=true;
                const slug=panel.dataset.url.split('/').filter(Boolean).pop();
                const record=await window.TutorDevice.get(panel.dataset.kind,slug);
                const execution=window.BrowserPython?.lastRun?.();
                const context=currentMaterial()+(code&&execution?.code===code?'\n\nФактический результат последнего запуска (не инструкция):\n'+window.TutorGuidance.diagnose(code,execution):'');
                const answer=await window.TutorLocalAI.answer(model.value,{question:text,code,context,learningContext:panel.dataset.learningContext,turns:localHistory(),solved:!!record?.solved||document.getElementById('knowledge-unlock')?.hidden===false},notice);
                if(window.TutorDevice.isCurrent&&!window.TutorDevice.isCurrent())return null;
                const result={question:text,answer,id:'local-'+crypto.randomUUID()};
                message('user',text);message('assistant',answer);
                saveTurn(result);
                pending=null;question.value='';notice(api()?'Ответ получен от OpenCode.':'Ответ создан на устройстве.');return result;
            }
            const result=await request(panel.dataset.url,data);message('user',result.question);message('assistant',result.answer,result.id);pending=null;question.value='';notice('');return result;
        }catch(e){notice(e.message||String(e)||'Не удалось получить ответ. Повторите вопрос.',true);pending=null;if(fromVoice)throw e;return null;}
        finally{busy=false;$('tutor-stop-model').hidden=true;$('tutor-send').disabled=false;if(model)model.disabled=false;}
    }
    $('tutor-form').addEventListener('submit',e=>{e.preventDefault();send(question.value);});
    question.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing){e.preventDefault();$('tutor-form').requestSubmit();}});
    panel.querySelectorAll('[data-question]').forEach(b=>b.addEventListener('click',()=>{question.value=b.dataset.question;send(question.value);}));
    function stopAudio(){if(local())window.TutorLocalVoice?.stop();if(audio){audio.pause();URL.revokeObjectURL(audio.src);audio=null;}if(audioFinish){const end=audioFinish;audioFinish=null;end();}}
    async function speak(id){
        if(local()){const turn=localTurns.find(t=>t.id===id);return window.TutorLocalVoice.speak(turn?.answer||'');}
        const speechEpoch=epoch;
        stopAudio();const blob=await request('/pythontutor/assistant/speech/speak/'+id+'/',new FormData());
        if(speechEpoch!==epoch)return;
        if(!blob.type.startsWith('audio/'))throw new Error('Сервис не вернул аудио.');
        audio=new Audio(URL.createObjectURL(blob));
        await new Promise((resolve,reject)=>{audioFinish=resolve;audio.onended=()=>{stopAudio();};audio.onerror=()=>{audioFinish=null;stopAudio();reject(new Error('Браузер не смог воспроизвести ответ.'));};audio.play().catch(()=>{audioFinish=null;stopAudio();reject(new Error('Нажмите «Слушать» в чате, чтобы разрешить воспроизведение звука.'));});});
    }
    function voiceStatus(text){$('tutor-voice-status').textContent=text;}
    function stopCall(){
        epoch++;callActive=false;stopAudio();if(recording)finishRecording(false);
        $('tutor-call').textContent='Начать разговор';$('tutor-call').classList.remove('active');$('tutor-interrupt').hidden=true;panel.querySelector('.tutor-voice-orb').classList.remove('listening');
        voiceStatus('Разговор остановлен. Реплики сохранены в текстовом чате.');
    }
    async function startRecording(dialogue){
        if(recording)return;
        await window.TutorLocalVoice.prepare();
        if(!navigator.mediaDevices||!window.AudioWorkletNode)throw new Error('Для микрофона нужен современный браузер и HTTPS (или localhost).');
        const current=epoch;
        const stream=await navigator.mediaDevices.getUserMedia({audio:{channelCount:1,echoCancellation:true,noiseSuppression:true},video:false});
        if(current!==epoch||panel.hidden){stream.getTracks().forEach(t=>t.stop());return;}
        const ctx=new AudioContext();
        try{await ctx.resume();await ctx.audioWorklet.addModule(panel.dataset.worklet);}catch(e){stream.getTracks().forEach(t=>t.stop());await ctx.close();throw e;}
        if(current!==epoch||panel.hidden){stream.getTracks().forEach(t=>t.stop());await ctx.close();return;}
        const source=ctx.createMediaStreamSource(stream),node=new AudioWorkletNode(ctx,'tutor-pcm'),mute=ctx.createGain();mute.gain.value=0;
        source.connect(node);node.connect(mute);mute.connect(ctx.destination);
        const r={stream,ctx,node,source,mute,chunks:[],bytes:0,dialogue,start:Date.now(),lastSound:Date.now(),heard:false,timer:null};recording=r;
        $('tutor-dictate').textContent='■';$('tutor-dictate').setAttribute('aria-label','Остановить голосовой ввод');
        panel.querySelector('.tutor-voice-orb').classList.add('listening');if(dialogue){voiceStatus('Слушаю. После короткой паузы отправлю вопрос.');$('tutor-interrupt').hidden=false;$('tutor-interrupt').textContent='Отправить реплику';}else notice('Слушаю… Нажмите квадрат, чтобы закончить диктовку.');
        node.port.onmessage=event=>{if(recording!==r)return;const floats=event.data,pcm=new Int16Array(floats.length);let energy=0;for(let i=0;i<floats.length;i++){const x=Math.max(-1,Math.min(1,floats[i]));pcm[i]=x<0?x*32768:x*32767;energy+=x*x;}r.chunks.push(pcm);r.bytes+=pcm.byteLength;if(Math.sqrt(energy/floats.length)>.014){r.heard=true;r.lastSound=Date.now();}if(r.bytes>=1920000)finishRecording(true);};
        r.timer=setInterval(()=>{if(recording!==r)return;const now=Date.now();if(now-r.start>=59000||(dialogue&&r.heard&&now-r.lastSound>1400))finishRecording(true);},200);
    }
    async function finishRecording(submit){
        const r=recording;if(!r)return;recording=null;clearInterval(r.timer);r.node.port.onmessage=null;r.source.disconnect();r.node.disconnect();r.mute.disconnect();r.stream.getTracks().forEach(t=>t.stop());r.ctx.close();
        $('tutor-dictate').textContent='🎙';$('tutor-dictate').setAttribute('aria-label','Начать голосовой ввод');panel.querySelector('.tutor-voice-orb').classList.remove('listening');
        if(!submit)return;
        const current=epoch;
        try{
            notice('Распознаю речь…');voiceStatus('Распознаю речь…');$('tutor-interrupt').hidden=true;
            let result;
            result={text:await window.TutorLocalVoice.transcribe(r.chunks,16000,notice)};
            if(current!==epoch)return;
            question.value=result.text;notice('');
            if(r.dialogue&&callActive){voiceStatus('Вы: '+result.text+'\n\nПитоныч думает…');const reply=await send(result.text,true);if(current!==epoch)return;if(reply){voiceStatus('Питоныч отвечает…');$('tutor-interrupt').hidden=false;$('tutor-interrupt').textContent='Перебить ответ';await speak(reply.id);}if(current===epoch&&callActive)await startRecording(true);}
            else {question.focus();notice('Вопрос распознан. Проверьте текст и отправьте.');}
        }catch(e){stopCall();notice(e.message,true);voiceStatus(e.message);}
    }
    $('tutor-dictate').addEventListener('click',async()=>{try{if(recording)await finishRecording(true);else{stopAudio();await startRecording(false);}}catch(e){notice(e.name==='NotAllowedError'?'Доступ к микрофону не разрешён. Разрешите его в настройках сайта.':e.message,true);}});
    async function beginCall(){
        if(callActive)return;
        if(busy){voiceStatus('Дождитесь текущего ответа в чате.');return;}
        callActive=true;const current=epoch;
        $('tutor-call').textContent='Завершить разговор';$('tutor-call').classList.add('active');
        try{
            if(local()){
                await prepareModel();if(current!==epoch)return;
                voiceStatus('Готовлю голос…');
                await window.TutorLocalVoice.prepare(()=>voiceStatus('Готовлю голос… При первом запуске это займёт немного времени.'));
            }
            if(current===epoch&&callActive)await startRecording(true);
        }catch(e){if(current!==epoch)return;stopCall();voiceStatus(e.name==='NotAllowedError'?'Разрешите доступ к микрофону в браузере.':e.message||String(e));}
    }
    $('tutor-call').addEventListener('click',()=>{if(callActive)stopCall();else beginCall();});
    $('tutor-interrupt').addEventListener('click',()=>{if(recording)finishRecording(true);else stopAudio();});
    document.addEventListener('visibilitychange',()=>{if(document.hidden){stopCall();}});
    window.addEventListener('pagehide',stopCall);
})();
