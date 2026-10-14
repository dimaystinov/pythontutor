(function () {
    'use strict';
    const panel=document.getElementById('tutor-panel');
    if(!panel) return;
    const $=id=>document.getElementById(id), launcher=$('tutor-launcher');
    let loaded=false,busy=false,voiceMode=false,callActive=false,recording=null,audio=null,audioFinish=null,epoch=0,voiceReady=false;
    let attachment=null,lastCode='',pending=null;
    const workspace=$('tutor-workspace'),divider=$('tutor-divider');
    const question=$('tutor-question'),log=$('tutor-messages'),status=$('tutor-status');
    const model=$('tutor-model');
    try { const choice=localStorage.getItem('tutor-ai-model');if(choice&&model?.querySelector('option[value="'+choice.replace(/[^\w.-]/g,'')+'"]'))model.value=choice; } catch(_){}
    const local=()=>!!model&&model.value!=='cloud';
    const chatKey='tutor-local-chat:'+window.TutorDevice.owner()+':'+panel.dataset.url;
    let localTurns=[],modelPromise=null,mathQueue=Promise.resolve();
    function friendlyProgress(text){
        const percent=String(text).match(/Загрузка модели: (\d+)%/);
        const label=percent?'Готовлю помощника · '+percent[1]+'%':String(text).includes('Модель готова')?'Готов к разговору':String(text).includes('Подготовка модели')?'Готовлю помощника…':text;
        notice(label);if(voiceMode)voiceStatus(label);
    }
    function prepareModel(){
        if(!local())return Promise.resolve();
        if(!modelPromise){model.disabled=true;modelPromise=window.TutorLocalAI.load(model.value,friendlyProgress).finally(()=>{modelPromise=null;model.disabled=busy;});}
        return modelPromise;
    }
    function localHistory(){try{localTurns=JSON.parse(localStorage.getItem(chatKey)||'[]');}catch(_){localTurns=[];}return localTurns;}
    function describeModel(){const c=window.TutorLocalAI?.choices.find(c=>c.id===model?.value);if($('tutor-model-info'))$('tutor-model-info').textContent=c?c.download+' загрузка, '+c.memory+'. '+c.note:'Обработка через настроенный API. Нужен интернет.';if($('tutor-load-model'))$('tutor-load-model').hidden=!c;if($('tutor-load-voice'))$('tutor-load-voice').hidden=!c;}
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
    function message(role,text,id){
        const item=document.createElement('div');item.className='tutor-message '+role;
        const body=document.createElement('div');body.className='message-body';formatted(body,text);item.append(body);
        if(role==='assistant'){
            const tools=document.createElement('div');tools.className='tutor-message-tools';
            const button=document.createElement('button');button.type='button';button.textContent='Копировать';button.addEventListener('click',()=>copy(text));tools.append(button);
            if(id&&voiceReady){const play=document.createElement('button');play.type='button';play.textContent='Слушать';play.addEventListener('click',async()=>{stopCall();try{await speak(id);}catch(e){notice(e.message,true);}});tools.append(play);}
            item.append(tools);
        }
        log.append(item);typesetMessage(body);log.scrollTop=log.scrollHeight;
    }
    async function history(){
        if(local()){
            log.querySelectorAll('.tutor-message').forEach(e=>e.remove());
            for(const turn of localHistory()){message('user',turn.question);message('assistant',turn.answer);}
            $('tutor-context').textContent='Питоныч · локальный помощник';
            voiceReady=true;loaded=true;$('tutor-voice-mode').disabled=false;$('tutor-dictate').disabled=false;
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
        try{sessionStorage.setItem('tutor-panel-open',open?'yes':'no');}catch(_){}launcher.setAttribute('aria-expanded',String(open));document.body.classList.toggle('tutor-open',open);window.dispatchEvent(new Event('resize'));
        if(open){updateCode();if(question&&!loaded)history();if(question)question.focus();}
        else {stopCall();if(recording)finishRecording(false);launcher.focus();}
    }
    launcher.addEventListener('click',()=>setOpen(true));$('tutor-close').addEventListener('click',()=>setOpen(false));
    $('tutor-expand').addEventListener('click',()=>{const full=panel.classList.toggle('fullscreen');$('tutor-expand').setAttribute('aria-pressed',String(full));$('tutor-expand').setAttribute('aria-label',full?'Вернуть боковую панель':'Развернуть на весь экран');});
    document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!panel.hidden)setOpen(false);});
    let initiallyOpen=window.innerWidth>=900;
    try{const saved=sessionStorage.getItem('tutor-panel-open');if(saved)initiallyOpen=saved==='yes';}catch(_){}
    if(initiallyOpen)setOpen(true);
    if(!question)return;
    model?.addEventListener('change',()=>{if(busy)return;stopCall();window.TutorLocalAI.stop();loaded=false;try{localStorage.setItem('tutor-ai-model',model.value);}catch(_){}describeModel();history();});
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
    function clearImage(){attachment=null;$('tutor-image').value='';$('tutor-attachment').hidden=true;}
    $('tutor-remove-image').addEventListener('click',clearImage);
    $('tutor-image').addEventListener('change',()=>{const file=$('tutor-image').files[0];if(!file){clearImage();return;}if(!['image/png','image/jpeg'].includes(file.type)||file.size>2*1024*1024){clearImage();notice('Выберите PNG или JPEG до 2 МБ.',true);return;}attachment=file;$('tutor-attachment').hidden=false;panel.querySelector('#tutor-attachment span').textContent=file.name;});
    async function send(text,fromVoice=false){
        if(busy)return null;text=text.trim();if(!text)return null;
        if(text.length>3000){notice('Сократите вопрос до 3000 символов.',true);return null;}
        updateCode();const code=$('tutor-include-code').checked?lastCode:'';
        if(code.length>12000){notice('Код слишком длинный. Сократите его или отключите передачу кода.',true);return null;}
        if(!pending||pending.text!==text||pending.code!==code)pending={text,code,id:crypto.randomUUID()};
        busy=true;$('tutor-stop-model').hidden=false;$('tutor-send').disabled=true;notice('Питоныч думает…');
        const data=new FormData();data.set('question',text);data.set('code',code);data.set('request_id',pending.id);if(attachment)data.set('image',attachment);
        try{
            if(local()){
                await prepareModel();
                if(attachment)throw Error('Локальные модели работают с текстом и кодом. Опишите изображение словами или выберите облачный режим.');
                model.disabled=true;
                const slug=panel.dataset.url.split('/').filter(Boolean).pop();
                const record=await window.TutorDevice.get(panel.dataset.kind,slug);
                const context=(document.querySelector('.main')||document.getElementById('tutor-content')).innerText;
                const answer=await window.TutorLocalAI.answer(model.value,{question:text,code,context,learningContext:panel.dataset.learningContext,turns:localHistory(),solved:!!record?.solved||document.getElementById('knowledge-unlock')?.hidden===false},notice);
                const result={question:text,answer,id:'local-'+crypto.randomUUID()};
                message('user',text);message('assistant',answer);
                localTurns.push(result);try{localStorage.setItem(chatKey,JSON.stringify(localTurns.slice(-20)));}catch(_){}
                pending=null;question.value='';notice('Ответ создан на устройстве.');return result;
            }
            const result=await request(panel.dataset.url,data);message('user',result.question);message('assistant',result.answer,result.id);pending=null;question.value='';clearImage();notice('');return result;
        }catch(e){notice(e.message||String(e)||'Не удалось получить ответ. Повторите вопрос.',true);pending=null;if(fromVoice)throw e;return null;}
        finally{busy=false;$('tutor-stop-model').hidden=true;$('tutor-send').disabled=false;if(model)model.disabled=false;}
    }
    $('tutor-form').addEventListener('submit',e=>{e.preventDefault();send(question.value|| (attachment?'Помоги понять, что показано на изображении.':''));});
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
            if(local())result={text:await window.TutorLocalVoice.transcribe(r.chunks,r.ctx.sampleRate,notice)};
            else {const data=new FormData();data.set('audio',new Blob(r.chunks,{type:'application/octet-stream'}),'speech.pcm');result=await request(panel.dataset.stt,data);}
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
