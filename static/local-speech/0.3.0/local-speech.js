/* LocalSpeech 0.3.0; host locally; no telemetry or cloud ASR. */
(function(module){

// model-catalog.js
const SPEECH_MODELS = {
 giga_multi: {label:'GigaAM Multilingual CTC INT8 · 225 МБ · эксперимент',files:['model.int8.onnx','tokens.txt'],online:false,multilingual:true,rate:16000,featureDim:64,field:'nemoCtc',model:'model.int8.onnx',experimental:true},
 whisper_small: {label:'Whisper small INT8 · 375 МБ · эксперимент',files:['small-encoder.int8.onnx','small-decoder.int8.onnx','small-tokens.txt'],online:false,preview:true,multilingual:true,rate:16000,whisper:'small',experimental:true},
 whisper_tiny: {label:"Whisper tiny INT8 · 104 МБ",files:["tiny-encoder.int8.onnx","tiny-decoder.int8.onnx","tiny-tokens.txt"],online:false,preview:true,multilingual:true,rate:16000,whisper:"tiny"},
 whisper: {label:'Whisper base INT8 · 161 МБ',files:['base-encoder.int8.onnx','base-decoder.int8.onnx','base-tokens.txt'],online:false,preview:true,multilingual:true,rate:16000,whisper:"base"},
 small: {label:'Zipformer INT8 · 29 МБ',files:['encoder.int8.onnx','decoder.onnx','joiner.int8.onnx','tokens.txt'],online:true,rate:16000,type:'zipformer2',encoder:'encoder.int8.onnx',joiner:'joiner.int8.onnx'},
 zipformer: {label:'Zipformer FP32 · 94 МБ',files:['encoder.onnx','decoder.onnx','joiner.onnx','tokens.txt'],online:true,rate:16000,type:'zipformer2',encoder:'encoder.onnx',joiner:'joiner.onnx'},
 large: {label:'GigaAM v3 RNNT INT8 · 232 МБ',files:['encoder.int8.onnx','decoder.onnx','joiner.onnx','tokens.txt'],online:false,rate:16000,type:'nemo_transducer',encoder:'encoder.int8.onnx',joiner:'joiner.onnx'},
 giga_ctc: {label:'GigaAM v3 CTC INT8 · 225 МБ',files:['model.int8.onnx','tokens.txt'],online:false,rate:16000,field:'nemoCtc',model:'model.int8.onnx'},
 tone: {label:'T-one CTC · 144 МБ',files:['model.onnx','tokens.txt'],online:true,rate:8000,field:'toneCtc',model:'model.onnx'}
};


// system-recognizer.js
/* No cloud fallback. The presence of SpeechRecognition alone is insufficient. */
function parseContextTerms(input) {
  return [...new Set(String(input).split(/[,;\n]/).map(s=>s.trim()).filter(Boolean))].slice(0,100).map(s=>[...s].slice(0,80).join(''));
}
class SystemRecognizer {
  constructor(API, emit, state, Phrase=globalThis.SpeechRecognitionPhrase) { this.API=API; this.Phrase=Phrase; this.emit=(...args)=>this.notify(emit,...args); this.state=(...args)=>this.notify(state,...args); this.active=false; this.generation=0; this.contextInfo={status:'not-requested',count:0}; }
  notify(callback,...args) {
    try{const result=callback?.(...args);if(result&&typeof result.catch==='function')result.catch(error=>{this.callbackError=error;});}
    catch(error){this.callbackError=error;}
  }
  async check(lang) {
    if(lang==='auto')return {status:'unsupported',message:'Для смешанной RU/EN речи используется многоязычная локальная модель. Включите микрофон для автоматического выбора резерва.'};
    if (!this.API || !('processLocally' in this.API.prototype) || typeof this.API.available!=='function')
      return {status:'unsupported',message:'Браузер не предоставляет подтверждённое локальное распознавание. Выберите локальную RU-модель.'};
    try {
      let timer;const status=await Promise.race([this.API.available({langs:[lang],processLocally:true}),new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('Проверка заняла больше 5 секунд')),5000);})]).finally(()=>clearTimeout(timer));
      const messages={available:'Браузер сообщает о локальной поддержке. Работа проверится на первой фразе.',downloadable:'Нужно установить системный языковой пакет.',downloading:'Браузер загружает языковой пакет. Повторите проверку позже.',unavailable:'Локальный пакет этого языка недоступен. Выберите другой язык или RU-модель.'};
      return {status,message:messages[status]||'Неизвестный статус системного движка.'};
    } catch(e) { return {status:'error',message:'Проверка локального движка: '+e.message}; }
  }
  async install(lang) {
    if(typeof this.API?.install!=='function')throw Error('Браузер не поддерживает установку языковых пакетов.');
    if(!await this.API.install({langs:[lang],processLocally:true}))throw Error('Языковой пакет не установлен.');
    return this.check(lang);
  }
  start(lang, sessionId, terms=[]) {
    if(!this.API || !('processLocally' in this.API.prototype))throw Error('Локальный режим недоступен.');
    // Structured hints are already phrases: UI delimiters must not split names.
    if(!Array.isArray(terms))throw new TypeError('terms must be an array');
    if(terms.length>100)throw new RangeError('At most 100 terms are supported');
    const preservedTerms=terms.map(term=>{
      if(typeof term!=='string'||!term.trim())throw new TypeError('Each term must be a nonempty string');
      if(term.length>80)throw new RangeError('Each term must contain at most 80 characters');
      if(/[\u0000-\u001f\u007f-\u009f\u2028\u2029]/u.test(term))throw new TypeError('Terms cannot contain control characters or line separators');
      return term;
    });
    this.dispose();
    this.active=true; this.sessionId=sessionId; this.lang=lang; this.segment=0; this.failures=0; this.hasInterim=false; this.lastResultAt=0;
    this.terms=preservedTerms;this.contextRejected=false;
    const generation=++this.generation;
    try{this.open(generation);}catch(error){this.dispose();throw error;}
  }
  open(generation) {
    if(!this.active||generation!==this.generation)return;
    clearTimeout(this.timer);this.timer=undefined;
    const previous=this.recognition;this.recognition=null;try{previous?.abort();}catch{}
    const r=new this.API(); this.recognition=r;this.nativeEnded=false; const ids=new Map(), finalized=new Set(), interim=new Map(); let hadResult=false;
    let interruptedReported=false, ended=false;
    const owns=()=>generation===this.generation&&this.recognition===r;
    const current=()=>owns()&&!ended;
    const ownSessionId=this.sessionId;
    const reportInterrupted=reason=>{
      if(interruptedReported)return;interruptedReported=true;
      for(const fragment of interim.values()){if(!owns())break;this.emit({type:'interrupted',sessionId:ownSessionId,...fragment,backend:'system',timingReliable:false,reason,turnComplete:false});}
    };
    this.reportInterrupted=reason=>{if(current())reportInterrupted(reason);};
    r.processLocally=true; r.continuous=true; r.interimResults=true; r.lang=this.lang;
    this.contextInfo={status:this.terms.length?'unsupported':'not-requested',count:0};
    if(this.terms.length&&!this.contextRejected&&'phrases' in r&&typeof this.Phrase==='function'){
      try{r.phrases=this.terms.map(term=>new this.Phrase(term,3));this.contextInfo={status:'applied',count:this.terms.length};}
      catch{this.contextInfo={status:'rejected',count:0};}
    }
    if(this.contextRejected)this.contextInfo={status:'rejected',count:0};
    this.state('context',this.contextInfo);
    r.onstart=()=>{if(current())this.state('listening');};
    r.onaudiostart=()=>{if(current())this.state('audio-started');};
    r.onspeechstart=()=>{if(current())this.state('speech-detected');};
    r.onresult=e=>{
      if(!current())return;
      for(let i=e.resultIndex;i<e.results.length;i++){
        if(!current())return;
        if(finalized.has(i))continue;
        const text=e.results[i][0].transcript.trim();
        if(!ids.has(i))ids.set(i,++this.segment);
        hadResult=true; this.failures=0; this.lastResultAt=Date.now();
        if(e.results[i].isFinal){finalized.add(i);interim.delete(i);}else interim.set(i,{segmentId:ids.get(i),text});
        this.hasInterim=interim.size>0;
        this.emit({type:e.results[i].isFinal?'final':'partial',sessionId:this.sessionId,segmentId:ids.get(i),text,backend:'system',timingReliable:false,reason:'recognizer',turnComplete:false,context:{...this.contextInfo}});
      }
    };
    r.onerror=e=>{
      if(!current())return;
      if(e.error==='no-speech')return;
      if(e.error==='phrases-not-supported'&&!this.contextRejected&&this.contextInfo.status==='applied'){
        this.contextRejected=true;this.contextInfo={status:'rejected',count:0};this.state('context',this.contextInfo);try{r.abort();}catch{r.onend();}return;
      }
      reportInterrupted(e.error);
      if(!current())return;
      this.active=false; ++this.generation; this.state('error','Системный движок: '+e.error+'. Облачный режим не включён.');
      try{r.abort();}catch{}
    };
    r.onend=()=>{
      if(!current())return;
      ended=true;this.nativeEnded=true;
      reportInterrupted('ended-before-final');
      if(!owns())return;
      this.emit({type:'clear-partial'});
      if(!owns())return;
      if(!this.active){this.state(interim.size?'stopped-incomplete':'stopped',interim.size?'Последняя фраза не подтверждена движком. Скачайте сохранённое аудио и проверьте незавершённый текст в отчёте.':undefined);return;}
      if(interim.size){this.active=false;++this.generation;this.state('error','Системный движок завершился без окончательного текста. Незавершённая речь передаётся локальному резерву.');return;}
      if(!hadResult&&++this.failures>3){this.active=false;this.state('error','Системный движок завершает сеанс без результатов. Проверьте язык и микрофон.');return;}
      this.state('restarting');
      if(!owns()||!this.active)return;
      this.timer=setTimeout(()=>{try{this.open(generation);}catch(e){this.dispose();this.state('error',e.message);}},350);
    };
    if(current())r.start();
  }
  endPhrase() { if(this.active&&this.hasInterim){this.hasInterim=false;try{this.recognition?.stop();}catch{}} }
  stop() { this.active=false; clearTimeout(this.timer);this.timer=undefined;if(this.nativeEnded){this.state('stopped');return;}try{this.recognition?.stop();}catch{} }
  stopTimedOut() { this.reportInterrupted?.('stop-timeout');this.dispose();this.state('stopped-incomplete','Движок не подтвердил завершение. Скачайте сохранённое аудио и проверьте незавершённый текст в отчёте.'); }
  dispose() { this.active=false; ++this.generation; this.reportInterrupted=null;clearTimeout(this.timer);this.timer=undefined;const recognition=this.recognition;this.recognition=null;try{recognition?.abort();}catch{} }
}
if(typeof module!=='undefined')module.exports={SystemRecognizer,parseContextTerms};


// capture.js
class MicrophoneCapture {
  constructor(onSamples,onEnded,options={}) {
    this.onSamples=onSamples;this.onEnded=onEnded;this.stopped=false;this.cleaned=false;
    this.stoppedTracks=new Set();
    this.workletURL=options.assetBaseURL===undefined?'pcm-worklet.js':new URL('pcm-worklet.js',new URL(options.assetBaseURL,globalThis.document?.baseURI||globalThis.location?.href)).href;
  }
  // Consumer callbacks may fail without taking ownership of capture cleanup.
  notify(callback,...args) {
    try{const result=callback?.(...args);if(result&&typeof result.catch==='function')result.catch(error=>{this.callbackError=error;});}
    catch(error){this.callbackError=error;}
  }
  start() {
    if(this.stopped)return Promise.reject(Error('Microphone capture is stopped. Create a new capture for another session.'));
    if(!this.startPromise)this.startPromise=this.open();
    return this.startPromise;
  }
  async open(){
    try {
      this.ctx=new AudioContext();
      await this.ctx.resume();
      if(this.stopped)return;
      const stream=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true,autoGainControl:true},video:false});
      this.stream=stream;
      // A permission dialog cannot be cancelled. A late grant must still release its tracks.
      if(this.stopped){this.stopTracks();return;}
      await this.ctx.audioWorklet.addModule(this.workletURL);
      if(this.stopped){this.stopTracks();return;}
      this.node=new AudioWorkletNode(this.ctx,'pcm-recorder');
      this.node.port.onmessage=({data})=>{
        if(this.cleaned)return;
        if(data.flushed)this.flushDone?.();
        else if(data.samples)this.notify(this.onSamples,data.samples,this.ctx.sampleRate);
      };
      this.source=this.ctx.createMediaStreamSource(this.stream);
      this.source.connect(this.node);this.node.connect(this.ctx.destination);
      for(const track of this.stream.getTracks())track.onended=()=>{
        if(this.stopped)return;
        this.notify(this.onEnded);
        void this.stop();
      };
    }catch(error){await this.stop();throw error;}
  }
  stop(){
    if(this.stopPromise)return this.stopPromise;
    this.stopped=true;this.stopPromise=Promise.resolve().then(()=>this.cleanup());return this.stopPromise;
  }
  stopTracks(){
    for(const track of this.stream?.getTracks()||[]){
      track.onended=null;
      if(this.stoppedTracks.has(track))continue;
      this.stoppedTracks.add(track);
      try{track.stop();}catch(error){this.cleanupError=error;}
    }
  }
  async cleanup(){
    if(this.node&&this.ctx?.state==='running')await new Promise(resolve=>{
      const finish=()=>{clearTimeout(timer);this.flushDone=null;resolve();};
      const timer=setTimeout(finish,300);this.flushDone=finish;
      try{this.node.port.postMessage('flush');}catch(error){this.cleanupError=error;finish();}
    });
    this.cleaned=true;this.flushDone=null;
    if(this.node)this.node.port.onmessage=null;
    this.stopTracks();
    for(const resource of [this.source,this.node])try{resource?.disconnect();}catch(error){this.cleanupError=error;}
    if(this.ctx&&this.ctx.state!=='closed')try{await this.ctx.close();}catch(error){this.cleanupError=error;}
  }
}
if(typeof module!=='undefined')module.exports={MicrophoneCapture};


// resilience.js
/* Pure policies shared by the UI and deterministic tests. */
class AudioReplayBuffer {
  constructor(maxSeconds=30){this.maxSeconds=maxSeconds;this.clear();}
  clear(){this.items=[];this.endMs=0;this.committedMs=0;this.lostMs=0;}
  push(samples,rate,isSpeech=true){
    const startMs=this.endMs;this.endMs+=samples.length/rate*1000;
    this.items.push({samples:samples.slice(),isSpeech,rate,startMs,endMs:this.endMs});
    while(this.items.length&&this.endMs-this.items[0].startMs>this.maxSeconds*1000){const old=this.items.shift();if(old.isSpeech&&old.endMs>this.committedMs)this.lostMs+=old.endMs-Math.max(old.startMs,this.committedMs);}
  }
  commit(endMs){this.committedMs=Math.max(this.committedMs,endMs);while(this.items.length&&this.items[0].endMs<=this.committedMs+.01)this.items.shift();}
  snapshot(){return this.items.filter(x=>x.endMs>this.committedMs+.01).map(x=>({...x,samples:x.samples.slice()}));}
}
function chooseFallback({current,attempted,lang,reason,largeAllowed=true}){
  // Russian-only assets must never silently replace an English recognizer.
  if(lang!=='ru-RU')return largeAllowed?['whisper_tiny',...(reason==='overload'?[]:['whisper'])].find(x=>x!==current&&!attempted.has(x))||null:null;
  const order=reason==='quality'?['tone','zipformer','whisper_tiny','whisper','small']:['small','zipformer','tone','whisper_tiny','whisper'];
  if(reason==='overload')return current==='small'?null:(!attempted.has('small')?'small':null);
  return order.find(x=>x!==current&&!attempted.has(x)&&(largeAllowed||x==='small'))||null;
}
function words(text){return (text||'').normalize('NFKC').toLocaleLowerCase().replace(/ё/g,'е').match(/[\p{L}\p{N}]+(?:['’-][\p{L}\p{N}]+)*/gu)||[];}
function assessQuality({text,durationMs=0,voicedMs=0,clippedRatio=0}){
  const tokens=words(text),flags=[];
  if(!tokens.length)flags.push('Речь обнаружена, но текст не получен');
  if(voicedMs>=4500&&tokens.length<=1)flags.push('Слишком мало текста для длительной речи');
  if(tokens.length>=6){const counts=new Map();for(const t of tokens)counts.set(t,(counts.get(t)||0)+1);if(Math.max(...counts.values())/tokens.length>.6)flags.push('Подозрительное повторение одного слова');}
  if(durationMs>0&&tokens.length/(durationMs/1000)>7)flags.push('Необычно много слов для длительности фразы');
  if(clippedRatio>.01)flags.push('Перегрузка микрофона: возможны искажения');
  return {status:flags.length?'review':'unverified',flags,wordCount:tokens.length,accuracy:null,note:flags.length?'Требуется проверка текста':'Явных признаков сбоя нет; точность без эталона неизвестна'};
}
function compareReference(reference,hypothesis){
  const a=words(reference),b=words(hypothesis);
  if(!a.length)return {error:'Введите эталонную фразу.'};
  if(a.length>1000||b.length>1000)return {error:'Для сравнения выберите не более 1000 слов.'};
  const matrix=Array.from({length:a.length+1},()=>new Uint16Array(b.length+1));
  for(let i=0;i<=a.length;i++)matrix[i][0]=i;
  for(let j=0;j<=b.length;j++)matrix[0][j]=j;
  for(let i=1;i<=a.length;i++)for(let j=1;j<=b.length;j++)matrix[i][j]=Math.min(matrix[i-1][j]+1,matrix[i][j-1]+1,matrix[i-1][j-1]+(a[i-1]===b[j-1]?0:1));
  const edits=[];let i=a.length,j=b.length,substitutions=0,deletions=0,insertions=0;
  while(i||j){
    if(i&&j&&a[i-1]===b[j-1]&&matrix[i][j]===matrix[i-1][j-1]){i--;j--;}
    else if(i&&j&&matrix[i][j]===matrix[i-1][j-1]+1){edits.push({type:'substitution',reference:a[i-1],hypothesis:b[j-1],referenceIndex:--i,hypothesisIndex:--j});substitutions++;}
    else if(i&&matrix[i][j]===matrix[i-1][j]+1){edits.push({type:'deletion',reference:a[i-1],hypothesis:'',referenceIndex:--i,hypothesisIndex:j});deletions++;}
    else{edits.push({type:'insertion',reference:'',hypothesis:b[j-1],referenceIndex:i,hypothesisIndex:--j});insertions++;}
  }
  edits.reverse();
  const ac=[...a.join(' ')],bc=[...b.join(' ')];let characterErrors=null;
  if(ac.length<=5000&&bc.length<=5000){
    let prev=Uint16Array.from({length:bc.length+1},(_,n)=>n),next=new Uint16Array(bc.length+1);
    for(let x=1;x<=ac.length;x++){next[0]=x;for(let y=1;y<=bc.length;y++)next[y]=Math.min(prev[y]+1,next[y-1]+1,prev[y-1]+(ac[x-1]===bc[y-1]?0:1));[prev,next]=[next,prev];}
    characterErrors=prev[bc.length];
  }
  return {referenceWords:a.length,hypothesisWords:b.length,wordErrors:matrix[a.length][b.length],werPercent:Math.round(matrix[a.length][b.length]/a.length*1000)/10,
    substitutions,deletions,insertions,edits,characterErrors,referenceCharacters:ac.length,cerPercent:characterErrors===null?null:Math.round(characterErrors/ac.length*1000)/10,
    normalization:'Регистр, пунктуация и ё/е нормализованы; дефисы внутри слов сохранены; числовые записи не преобразуются. CER включает пробелы; рассчитан до 5000 символов.'};
}
if(typeof module!=='undefined')module.exports={AudioReplayBuffer,chooseFallback,assessQuality,compareReference};


// device-policy.js
/* Hints are approximate and often absent (Safari); runtime measurements override them. */
function readDeviceHints(nav=globalThis.navigator){
  const positive=value=>Number.isFinite(value)&&value>0?value:null;
  return {cores:positive(nav?.hardwareConcurrency),memoryGB:positive(nav?.deviceMemory),mobile:/Android|iPhone|iPad|Mobile/i.test(nav?.userAgent||'')||(/Mac/.test(nav?.platform||'')&&(nav?.maxTouchPoints||0)>1),saveData:nav?.connection?.saveData===true};
}
function selectDevicePlan(hints,{language='ru-RU',largeAllowed=true,refine=true}={}){
  const ru=language==='ru-RU',limited=(hints.cores!==null&&hints.cores<=2)||(hints.memoryGB!==null&&hints.memoryGB<=4)||hints.mobile;
  const unknown=hints.cores===null||hints.memoryGB===null;
  const primary=ru?'small':largeAllowed?'whisper_tiny':null;
  let second=null,reason='Уточнение отключено';
  if(refine&&largeAllowed){
    if(limited)reason='Экономный режим: мобильное устройство, мало памяти или ядер';
    else if(unknown)reason='Память или процессор скрыты браузером: тяжёлое уточнение автоматически не загружается';
    else if(hints.memoryGB>=8&&hints.cores>=4){second=ru?'large':'whisper';reason='Уточнение разрешено после измерения скорости первого прохода';}
    else reason='Недостаточно подтверждённых ресурсов для двух моделей одновременно';
  }
  return {preferred:'system',primary,refiner:second,reason,tier:limited?'light':unknown?'unknown':second?'capable':'balanced',avoidAutomaticDownload:hints.saveData};
}
function allowRefinement(plan,metrics={}){
  if(!plan.refiner)return false;
  // At least two seconds of real work, with headroom for capture and the other worker.
  return metrics.audioMs>=2000&&metrics.processingMs/metrics.audioMs<.35&&(metrics.recentQueueMs||0)<250;
}
if(typeof module!=='undefined')module.exports={readDeviceHints,selectDevicePlan,allowRefinement};


// recognition-policy.js
/* Pure selection policy. Capability probes and observed speed belong to the host.
 * A candidate is permission to try, never proof of language accuracy or speed. */
(function (root) {
  'use strict';
  const TERM_LIMIT = 32;
  const TERM_LENGTH_LIMIT = 80;

  function normalizeRecognitionLanguage(value = 'ru') {
    if (typeof value !== 'string') throw new TypeError('language must be a supported language string');
    const tag = value.trim().toLowerCase();
    if (tag === 'ru' || tag === 'ru-ru') return {language: 'ru', workerLanguage: 'ru', systemLocale: 'ru-RU'};
    if (tag === 'en' || tag === 'en-us' || tag === 'en-gb') {
      return {language: 'en', workerLanguage: 'en', systemLocale: tag === 'en-gb' ? 'en-GB' : 'en-US'};
    }
    if (tag === 'mixed' || tag === 'auto') return {language: tag, workerLanguage: 'auto', systemLocale: null};
    throw new RangeError('Unsupported language: use ru, ru-RU, en, en-US, en-GB, mixed or auto');
  }

  function validateRecognitionTerms(terms = []) {
    if (!Array.isArray(terms)) throw new TypeError('terms must be an array');
    if (terms.length > TERM_LIMIT) throw new RangeError(`At most ${TERM_LIMIT} terms are supported`);
    return terms.map(term => {
      if (typeof term !== 'string' || !term.trim()) throw new TypeError('Each term must be a nonempty string');
      if (term.length > TERM_LENGTH_LIMIT) throw new RangeError(`Each term must contain at most ${TERM_LENGTH_LIMIT} characters`);
      if (/[\u0000-\u001f\u007f-\u009f\u2028\u2029]/u.test(term)) throw new TypeError('Terms cannot contain control characters or line separators');
      // Preserve names, scripts, punctuation, numbers and negations verbatim.
      return term;
    });
  }

  function normalizedHints(hints) {
    const source = hints && typeof hints === 'object' ? hints : {};
    const positive = value => typeof value === 'number' && Number.isFinite(value) && value > 0 ? value : null;
    return {cores: positive(source.cores), memoryGB: positive(source.memoryGB), mobile: source.mobile === true, saveData: source.saveData === true};
  }

  function contextCapability(engine, model) {
    if (engine === 'system') return {
      supported: 'conditional', mechanism: 'phrases',
      note: 'Only when the verified on-device recognizer exposes phrase biasing; otherwise terms remain unapplied.'
    };
    if (model === 'small' || model === 'zipformer') return {
      supported: 'conditional', mechanism: 'zipformer-hotwords',
      note: 'Requires modified beam search and tokenizer-compatible Russian terms. Latin technical names are not automatically transliterated.'
    };
    return {supported: false, mechanism: null, note: 'This adapter does not apply contextual terms to this model. Raw transcription is preserved.'};
  }

  function candidate(engine, model, rank) {
    return {key: engine === 'system' ? 'system' : model, engine, model, resourceRank: rank,
      requiresOnDevice: true, context: contextCapability(engine, model)};
  }

  function selectRecognitionPlan(hints = {}, {language = 'ru', allowLargeModels = true, cacheOnly = false, terms = []} = {}) {
    for (const [name, value] of Object.entries({allowLargeModels, cacheOnly})) {
      if (typeof value !== 'boolean') throw new TypeError(`${name} must be boolean`);
    }
    const normalized = normalizeRecognitionLanguage(language);
    const checkedTerms = validateRecognitionTerms(terms);
    const device = normalizedHints(hints);
    const unknown = device.cores === null || device.memoryGB === null;
    const limited = device.mobile || (device.cores !== null && device.cores <= 2) || (device.memoryGB !== null && device.memoryGB <= 4);
    const capable = !device.mobile && !unknown && device.memoryGB >= 8 && device.cores >= 4;
    const tier = limited ? 'light' : unknown ? 'unknown' : capable ? 'capable' : 'balanced';
    const candidates = [];
    const notes = [
      'System recognition must pass an explicit on-device and language availability probe; network recognition is never an implicit fallback.',
      'Device hints only bound initial choices. Runtime load failures and measured processing speed can require degradation.',
      'No model confidence is represented as a percentage of transcription accuracy.'
    ];
    if (normalized.systemLocale) candidates.push(candidate('system', null, null));
    else notes.push('Mixed/auto mode bypasses fixed-locale system recognition. Per-segment language detection does not guarantee accurate code switching.');

    if (normalized.language === 'ru') {
      candidates.push(candidate('local', 'small', 1));
      if (capable && allowLargeModels) {
        candidates.push(candidate('local', 'zipformer', 2), candidate('local', 'giga_ctc', 3));
      }
    } else {
      if (capable && allowLargeModels) candidates.push(candidate('local', 'whisper', 2));
      candidates.push(candidate('local', 'whisper_tiny', 1));
    }
    if (!allowLargeModels) notes.push('Large-model opt-out retains the smallest supported local route: Russian Zipformer INT8 or multilingual Whisper tiny.');
    if (device.saveData) notes.push('Data-saving mode requires cached local assets; missing assets must fail without downloading.');
    if (checkedTerms.length) notes.push('Terms are hints only where the selected engine supports them; no transcription rewriting is authorized.');
    return {...normalized, tier, cacheOnly: cacheOnly || device.saveData, allowLargeModels,
      terms: checkedTerms, candidates, primary: candidates[0] || null, fallbacks: candidates.slice(1),
      maxAttempts: candidates.length, notes};
  }

  function selectRecognitionFallback(plan, {attempted = [], reason = 'failure', current = null} = {}) {
    if (!plan || !Array.isArray(plan.candidates)) throw new TypeError('A recognition plan is required');
    if (!(attempted instanceof Set) && !Array.isArray(attempted)) throw new TypeError('attempted must be a Set or array of candidate keys');
    const used = new Set(attempted);
    const currentKey = typeof current === 'string' ? current : current && current.key;
    const active = plan.candidates.find(item => item.key === currentKey);
    if (currentKey) used.add(currentKey);
    const overloaded = ['overload', 'queue-overflow', 'slow'].includes(reason);
    if (overloaded && (!active || active.engine !== 'local')) return null;
    return plan.candidates.find(item => !used.has(item.key) && (!overloaded || (
      item.engine === 'local' && item.resourceRank < active.resourceRank
    ))) || null;
  }

  const api = {normalizeRecognitionLanguage, validateRecognitionTerms, selectRecognitionPlan, selectRecognitionFallback};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.SpeechRecognitionPolicy = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);


// local-engine.js
class LocalEngine {
  constructor(model,onEvent=()=>{},onError=()=>{},{assetBaseURL}={}){
    if(typeof SPEECH_MODELS==='undefined'||!Object.prototype.hasOwnProperty.call(SPEECH_MODELS,model))throw Error('Неизвестная модель: '+model);
    this.assetBaseURL=assetBaseURL===undefined?null:new URL(assetBaseURL).href;
    this.model=model;this.onEvent=onEvent;this.onError=onError;this.pending=new Map();this.closed=false;this.sequence=0;
    this.metrics={maxQueueMs:0,packets:0};this.abort=new AbortController();this.transcription=null;this.resolveLoad=null;this.rejectLoad=null;this.resolveEnd=null;this.rejectEnd=null;this.sessionId=null;
  }
  assetURL(path){return this.assetBaseURL?new URL(path,this.assetBaseURL).href:path;}
  async load(progress=()=>{},{cacheOnly=false,language="ru",vadMode="silero",contextTerms=[],contextScore=1.5,beamSearch=false}={}){
    if(this.closed)throw this.failure||Error('Движок закрыт');
    if(this.loading||this.worker)throw Error('Модель уже загружается или загружена');
    this.loading=true;
    let cacheHits=0,downloadedBytes=0;const cacheWarnings=[];
    const timeout=setTimeout(()=>this.abort.abort(),60000);
    try{
      let cache;
      try{cache=await caches.open('local-speech-verified-v1');}catch{cacheWarnings.push('Хранилище моделей недоступно');}
      const manifestURL=this.assetURL('evidence/model-manifest.json');let response;
      if(cacheOnly){
        try{response=await cache?.match(manifestURL);}catch{}
        if(!response)try{response=await caches.match(manifestURL);}catch{}
      }else response=await fetch(manifestURL,{signal:this.abort.signal});
      if(!response?.ok)throw Error('Не удалось прочитать контрольные суммы моделей.');
      const manifest=await response.json(),seen=new Set();
      if(!Array.isArray(manifest)||!manifest.every(entry=>{
        if(!entry||typeof entry.model!=='string'||!/^[a-zA-Z0-9_-]+$/.test(entry.model)||typeof entry.file!=='string'||!/^[a-zA-Z0-9][a-zA-Z0-9_.-]*$/.test(entry.file)||!Number.isSafeInteger(entry.bytes)||entry.bytes<=0||typeof entry.sha256!=='string'||!/^[a-f0-9]{64}$/.test(entry.sha256))return false;
        const key=entry.model+'/'+entry.file;if(seen.has(key))return false;seen.add(key);return true;
      }))throw Error('Некорректный манифест моделей');
      if(!cacheOnly&&cache){
        try{await cache.put(manifestURL,new Response(JSON.stringify(manifest),{headers:{'Content-Type':'application/json'}}));}
        catch{cacheWarnings.push('Не удалось сохранить манифест моделей; повторная загрузка может потребовать сеть');}
      }
      const files=[];
      const assets=SPEECH_MODELS[this.model].files.map(name=>({model:this.model,name}));
      if(vadMode==='silero')assets.push({model:'vad',name:'silero_vad.onnx'});
      if(contextTerms.length&&['small','zipformer'].includes(this.model))assets.push({model:'context',name:'ru-bpe.vocab'});
      for(const {model,name} of assets){
        try{
        if(this.closed)throw Error('Загрузка отменена');
        const entry=manifest.find(x=>x.model===model&&x.file===name);
        if(!entry)throw Error('Нет контрольной суммы '+name);
        const url=this.assetURL(`models/${model}/${name}`),key=url+'?sha256='+entry.sha256;
        let buffer;try{const saved=await cache?.match(key);if(saved)buffer=await saved.arrayBuffer();}catch{}
        const verify=async bytes=>{
          if(bytes.byteLength!==entry.bytes)return false;
          const digest=await crypto.subtle.digest('SHA-256',bytes);
          return [...new Uint8Array(digest)].map(x=>x.toString(16).padStart(2,'0')).join('')===entry.sha256;
        };
        if(buffer&&!await verify(buffer)){await cache?.delete(key);buffer=null;}
        if(buffer)cacheHits++;
        if(!buffer){
          if(cacheOnly)throw Error("Модель не сохранена или повреждена: "+name);
          progress('Загрузка '+name,files.length/assets.length);
          const r=await fetch(url,{signal:this.abort.signal});if(!r.ok)throw Error(name+': HTTP '+r.status);
          buffer=await r.arrayBuffer();downloadedBytes+=buffer.byteLength;if(!await verify(buffer))throw Error('Контрольная сумма не совпала: '+name);
          try{await cache?.put(key,new Response(buffer));}catch{cacheWarnings.push('Не удалось сохранить '+name+'; повторная загрузка может потребовать сеть');}
        }
        files.push({name,buffer});
        }catch(e){if(!['vad','context'].includes(model)||this.closed||this.abort.signal.aborted)throw e;cacheWarnings.push((model==='vad'?'Silero недоступен; используется порог громкости: ':'Словарь подсказок недоступен; распознавание без подсказок: ')+e.message);}
      }
      if(this.closed)throw Error('Загрузка отменена');
      progress('Инициализация '+SPEECH_MODELS[this.model].label,1);
      this.worker=new Worker(this.assetURL('worker.js'));
      this.worker.onerror=e=>this.error(Error(e.message));
      this.worker.onmessage=({data:d})=>{
        if(this.closed)return;
        if(d.type==='error'){this.error(Error(d.message));return;}
        if(d.type==='ready'){clearTimeout(this.initTimer);const resolve=this.resolveLoad;this.resolveLoad=this.rejectLoad=null;resolve?.(d);return;}
        if(d.type==='transcribed'&&this.transcription?.id===d.id){clearTimeout(this.transcription.timer);const job=this.transcription;this.transcription=null;job.resolve(d);return;}
        if(d.type==='transcribed')return;
        if(['begun','partial','final','ack','processing','preview-policy','ended'].includes(d.type)&&(this.sessionId===null||d.sessionId!==this.sessionId))return;
        if(d.sessionId!==undefined&&d.sessionId!==this.sessionId)return;
        if(d.type==='processing'&&d.sessionId===this.sessionId){
          const valid=d.action==='audio'?this.pending.has(d.packetId):d.action==='end'&&Boolean(this.resolveEnd);
          if(valid){
            this.metrics.lastProcessing={...d};
            if(d.state==='start')this.processing={...d,observedAt:Date.now()};
            else if(d.state==='end'&&this.processing?.packetId===d.packetId&&this.processing?.stage===d.stage)this.processing=null;
          }
        }
        if(d.type==='preview-policy')this.metrics.previewPolicy={...d};
        if(d.type==='ack'){const item=this.pending.get(d.id);if(item){this.pending.delete(d.id);this.metrics.maxQueueMs=Math.max(this.metrics.maxQueueMs,Date.now()-item.time);this.metrics.packets++;d.queueMs=Date.now()-item.time;d.queueDepth=this.pending.size;this.metrics.recentQueueMs=d.queueMs;this.metrics.audioMs=(this.metrics.audioMs||0)+(d.audioMs||0);this.metrics.processingMs=(this.metrics.processingMs||0)+(d.processingMs||0);item.resolve();}}
        if(d.type==='ended'){if(!this.resolveEnd)return;clearTimeout(this.endTimer);const resolve=this.resolveEnd;this.resolveEnd=this.rejectEnd=null;this.endedSessionId=this.sessionId;this.sessionId=null;this.processing=null;resolve();}
        this.onEvent(d);
      };
      const ready=new Promise((resolve,reject)=>{this.resolveLoad=resolve;this.rejectLoad=reject;this.initTimer=setTimeout(()=>this.close(Error('Инициализация модели дольше 30 секунд')),30000);});
      try{this.worker.postMessage({action:'load',model:this.model,language,contextTerms,contextScore,beamSearch,files},files.map(f=>f.buffer));}catch(e){this.close(e);}
      const result=await ready;
      if(this.closed)throw this.failure||Error('Движок закрыт');
      this.watchdog=setInterval(()=>{
        const first=this.pending.values().next().value;
        if(first&&Date.now()-first.time>8000)this.error(this.timeoutError('Движок не подтверждает обработку аудио 8 секунд'));
      },1000);
      return {...result,cacheHits,downloadedBytes,cacheWarnings};
    }catch(e){this.close(e);throw e;}finally{clearTimeout(timeout);this.loading=false;}
  }
  begin(options){
    if(this.closed||!this.worker||this.loading)throw this.failure||Error('Движок закрыт или не загружен');
    if(!options||typeof options.sessionId!=='string'||!options.sessionId)throw Error('Неверный идентификатор сеанса');
    if(this.sessionId!==null||this.resolveEnd||this.pending.size||this.transcription)throw Error('Предыдущий сеанс ещё не завершён');
    this.sessionId=options.sessionId;this.endedSessionId=null;this.endPromise=null;this.processing=null;this.metrics={maxQueueMs:0,packets:0};
    try{this.worker.postMessage({...options,action:'begin'});}catch(e){this.close(e);throw e;}
  }
  validateAudio(samples,sampleRate){
    if(Object.prototype.toString.call(samples)!=='[object Float32Array]'||!samples.length||!samples.every(Number.isFinite))throw Error('Некорректный PCM');
    if(!Number.isInteger(sampleRate)||sampleRate<8000||sampleRate>96000)throw Error('Некорректная частота аудио');
    // A view may cover only part of a microphone buffer. Never send the surrounding samples.
    return samples.byteOffset||samples.byteLength!==samples.buffer.byteLength?samples.slice():samples;
  }
  timeoutError(message){
    const first=this.pending.entries().next().value,processing=this.processing?{...this.processing,elapsedMs:Date.now()-this.processing.observedAt}:null;
    const error=Error(message+(processing?' · этап '+processing.stage+(processing.packetId!==null?', пакет '+processing.packetId:''):''));
    error.code='timeout';error.processing=processing;error.pendingAudio={queueDepth:this.pending.size,oldestPacketId:first?.[0]??null,oldestAgeMs:first?Date.now()-first[1].time:0};return error;
  }
  transcribe(samples,sampleRate,id,timeoutMs=15000){
    if(this.closed||!this.worker||this.loading)return Promise.reject(this.failure||Error('Движок уточнения закрыт'));
    if(this.transcription||this.sessionId!==null)return Promise.reject(Error('Движок уточнения занят'));
    try{samples=this.validateAudio(samples,sampleRate);if(samples.length/sampleRate>20||!Number.isFinite(timeoutMs)||timeoutMs<=0)throw Error('Недопустимый фрагмент или время уточнения');}catch(e){return Promise.reject(e);}
    return new Promise((resolve,reject)=>{
      const timer=setTimeout(()=>this.close(Error('Уточнение превысило допустимое время')),timeoutMs);
      this.transcription={id,resolve,reject,timer};
      try{this.worker.postMessage({action:'transcribe',id,sampleRate,samples:samples.buffer},[samples.buffer]);}catch(e){this.close(e);}
    });
  }
  audio(samples,sampleRate,sessionId,hints={}){
    if(this.closed||!this.worker||this.loading)return Promise.reject(this.failure||Error('Движок закрыт'));
    if(!this.sessionId||sessionId!==this.sessionId||this.resolveEnd)return Promise.reject(Error('Неверный или завершённый сеанс'));
    try{samples=this.validateAudio(samples,sampleRate);}catch(e){return Promise.reject(e);}
    if(!hints||typeof hints!=='object'||Array.isArray(hints))return Promise.reject(Error('Audio hints must be an object'));
    const pendingPackets=hints.pendingPackets===undefined?0:hints.pendingPackets;
    if(!Number.isSafeInteger(pendingPackets)||pendingPackets<0||pendingPackets>150)return Promise.reject(Error('pendingPackets must be an integer from 0 to 150'));
    if(this.pending.size>=50){const e=Error('Перегрузка: очередь аудио больше 5 секунд');e.code='overload';return Promise.reject(e);}
    const id=++this.sequence;
    return new Promise((resolve,reject)=>{
      this.pending.set(id,{resolve,reject,time:Date.now()});
      try{this.worker.postMessage({action:'audio',sessionId,id,sampleRate,queueDepth:Math.max(this.pending.size,pendingPackets),samples:samples.buffer},[samples.buffer]);}catch(e){this.close(e);}
    });
  }
  end(sessionId,sampleRate){
    if(this.closed||!this.worker||this.loading)return Promise.reject(this.failure||Error('Движок закрыт'));
    if(typeof sessionId!=='string'||!sessionId)return Promise.reject(Error('Неверный сеанс'));
    if(sessionId===this.endedSessionId&&this.sessionId===null)return Promise.resolve();
    if(!this.sessionId||sessionId!==this.sessionId)return Promise.reject(Error('Неверный сеанс'));
    if(this.resolveEnd)return this.endPromise;
    if(!Number.isInteger(sampleRate)||sampleRate<8000||sampleRate>96000)return Promise.reject(Error('Некорректная частота аудио'));
    this.endPromise=new Promise((resolve,reject)=>{
      this.resolveEnd=resolve;this.rejectEnd=reject;this.endTimer=setTimeout(()=>this.error(this.timeoutError('Завершение модели дольше 15 секунд')),15000);
      try{this.worker.postMessage({action:'end',sessionId,sampleRate});}catch(e){this.close(e);}
    });
    return this.endPromise;
  }
  error(e){if(this.closed)return;this.close(e);this.onError(e);}
  close(reason){
    if(this.closed)return;this.closed=true;if(reason)this.failure=reason;const error=this.failure||Error('Движок закрыт');
    this.abort.abort();clearTimeout(this.initTimer);clearTimeout(this.endTimer);clearInterval(this.watchdog);this.worker?.terminate();
    const rejectLoad=this.rejectLoad,rejectEnd=this.rejectEnd;this.resolveLoad=this.rejectLoad=this.resolveEnd=this.rejectEnd=null;
    rejectLoad?.(error);rejectEnd?.(error);
    if(this.transcription){clearTimeout(this.transcription.timer);this.transcription.reject(error);this.transcription=null;}
    for(const x of this.pending.values())x.reject(error);this.pending.clear();this.sessionId=null;this.processing=null;
  }
}


// sdk/local-speech.js
/* Headless browser API. Bundled with pinned local adapters by tools/build-sdk.cjs. */
(function(root){
  'use strict';
  const {selectRecognitionPlan,selectRecognitionFallback}=root.SpeechRecognitionPolicy;
  const scriptBase=typeof document!=='undefined'&&document.currentScript?.src?new URL('.',document.currentScript.src).href:null;
  // Backend scores are uncalibrated and must align with the exact transcript.
  function assessWords(text, evidence=[]) {
    const words=String(text).match(/[\p{L}\p{N}_]+(?:[-'][\p{L}\p{N}_]+)*/gu)||[];
    const normalize=s=>String(s).toLowerCase().replace(/ё/g,'е');
    const matched=Array.isArray(evidence)&&evidence.length===words.length&&evidence.every((w,i)=>w&&normalize(String(w.word).trim().replace(/^[^\p{L}\p{N}]+|[^\p{L}\p{N}]+$/gu,''))===normalize(words[i]));
    return words.map((word,i)=>{const p=matched?evidence[i].probability:null;return {word,probability:typeof p==='number'&&Number.isFinite(p)&&p>=0&&p<=1?p:null,calibrated:false,languageProbability:null};});
  }
  class SpeechClient {
    constructor(options={}){
      const base=options.assetBaseURL||scriptBase;
      if(!base)throw Error('assetBaseURL is required');
      this.assetBaseURL=new URL(base,root.location?.href).href;
      if(!this.assetBaseURL.endsWith('/'))throw Error('assetBaseURL must end with /');
      if(root.location&&new URL(this.assetBaseURL).origin!==root.location.origin)throw Error('Serve speech assets on the application origin');
      this.options={language:'ru',allowLargeModels:true,cacheOnly:false,terms:[],pauseSeconds:.7,maxSegmentSeconds:12,...options};
      if(!Number.isFinite(this.options.pauseSeconds)||this.options.pauseSeconds<.3||this.options.pauseSeconds>2)throw Error('pauseSeconds must be 0.3..2');
      if(!Number.isFinite(this.options.maxSegmentSeconds)||this.options.maxSegmentSeconds<3||this.options.maxSegmentSeconds>20)throw Error('maxSegmentSeconds must be 3..20');
      this.hints=options.deviceHints===undefined?readDeviceHints():{...options.deviceHints};this.plan=selectRecognitionPlan(this.hints,this.options);
      this.state='idle';this.listeners=new Map();this.epoch=0;this.startEpoch=0;this.backendEpoch=0;
      this.buffer=new AudioReplayBuffer(30);this.attempted=new Set();this.finalized=new Set();this.segmentBase=0;this.nativeOverlapMs=0;
    }
    on(type,listener){if(typeof listener!=='function')throw TypeError('Listener must be a function');if(!this.listeners.has(type))this.listeners.set(type,new Set());this.listeners.get(type).add(listener);return ()=>this.listeners.get(type)?.delete(listener);}
    emit(type,data={}){const event={...data,type,schemaVersion:1};for(const fn of [...(this.listeners.get(type)||[]),...(this.listeners.get('*')||[])]){try{fn(event);}catch{/* Host observers cannot break capture or cleanup. */}}}
    setState(state,detail={}){this.state=state;queueMicrotask(()=>this.emit('state',{state,...detail}));}
    assertOpen(){if(this.state==='disposed'||this.disposing)throw Error('Speech client is disposed');}
    async prepare({input='microphone'}={}){
      this.assertOpen();if(!['microphone','pcm'].includes(input))throw Error('input must be microphone or pcm');
      if(this.state==='preparing'){if(input!==this.input)throw Error('Input mode cannot change during prepare');return this.preparing;}
      if(this.state==='ready'&&this.input===input)return this.diagnostics();
      if(!['idle','ready','error'].includes(this.state))throw Error('Stop the session before preparing');
      this.closeBackend();this.candidate=null;this.input=input;this.attempted=new Set();const epoch=++this.epoch;this.setState('preparing');
      const job=(async()=>{try{await this.nextBackend(epoch,'failure');if(epoch!==this.epoch)throw Error('Preparation cancelled');this.setState('ready');return this.diagnostics();}catch(error){if(epoch===this.epoch){this.closeBackend();this.setState('error');this.emit('error',{code:'prepare-failed',message:error.message});}throw error;}})();
      this.preparing=job;return job;
    }
    async nextBackend(epoch,reason,lastFailure){
      let candidate;
      while(epoch===this.epoch&&(candidate=selectRecognitionFallback(this.plan,{attempted:this.attempted,reason,current:this.candidate}))){
        this.attempted.add(candidate.key);if(this.input==='pcm'&&candidate.engine==='system')continue;
        this.closeBackend();const backendEpoch=++this.backendEpoch;this.candidate=candidate;
        const current=()=>epoch===this.epoch&&backendEpoch===this.backendEpoch&&this.state!=='disposed';
        try{
          if(candidate.engine==='system'){
            const adapter=new SystemRecognizer(root.SpeechRecognition||root.webkitSpeechRecognition,d=>{if(current())this.result(d);},(state,message)=>{if(!current())return;if(state==='error')this.recover(Error(String(message)),'failure');if(state==='context')this.emit('context',message);if(state==='stopped'||state==='stopped-incomplete')this.systemStopped?.(state);});
            this.system=adapter;const check=await adapter.check(this.plan.systemLocale);if(!current())throw Error('Preparation cancelled');if(check.status!=='available')throw Error(check.message||check.status);
            this.loadStats={backend:'system',localOnly:true};
          }else{
            const adapter=new LocalEngine(candidate.model,d=>{if(current())this.result(d);},error=>{if(current()&&['listening','starting'].includes(this.state))this.recover(error,error.code||'failure');},{assetBaseURL:this.assetBaseURL});this.engine=adapter;
            this.loadStats=await adapter.load((message,progress)=>{if(current())this.emit('progress',{message,progress});},{cacheOnly:this.plan.cacheOnly,language:this.plan.workerLanguage,contextTerms:this.plan.terms,pauseSeconds:this.options.pauseSeconds});
            if(!current()){adapter.close();throw Error('Preparation cancelled');}
          }
          this.emit('backend',{backend:candidate.key,localOnly:true,contextCapability:candidate.context,context:this.loadStats.context||{status:'not-reported',count:0},load:this.loadStats});return;
        }catch(error){if(epoch!==this.epoch)throw error;lastFailure=error;this.closeBackend();this.emit('warning',{code:'backend-unavailable',backend:candidate.key,message:error.message});}
      }
      if(lastFailure){
        const failure=Error(`Local backend ${this.candidate?.key||'unknown'} failed: ${lastFailure.message}. No eligible local fallback remains.`);
        failure.code=lastFailure.code||'backend-failed';failure.cause=lastFailure;
        failure.processing=lastFailure.processing;failure.pendingAudio=lastFailure.pendingAudio;
        throw failure;
      }
      throw Error('No usable local speech backend for this language and resource policy');
    }
    start({input='microphone'}={}){
      this.assertOpen();if(this.startTask)return this.startTask;if(['listening','recovering','stopping'].includes(this.state))return Promise.reject(Error('Session is already active'));
      const startEpoch=++this.startEpoch;
      const job=(async()=>{
        await this.prepare({input});if(startEpoch!==this.startEpoch)throw Error('Start cancelled');
        this.sessionId=crypto.randomUUID();this.buffer.clear();this.finalized.clear();this.segmentBase=0;this.nativeOverlapMs=0;this.rate=null;this.quietMs=0;this.speechSinceTextMs=0;this.recovery=null;this.setState('starting');
        const epoch=this.epoch;const current=()=>epoch===this.epoch&&startEpoch===this.startEpoch;
        try{
          if(this.engine)this.beginEngine(0);
          if(input==='microphone'){
            const capture=new MicrophoneCapture((samples,rate)=>{if(current()||(epoch===this.epoch&&this.flushing))return this.accept(samples,rate).catch(error=>{if(current())return this.fail(error);});},()=>{if(current()){this.emit('warning',{code:'microphone-ended',message:'Microphone disconnected'});this.stop();}},{assetBaseURL:this.assetBaseURL});
            this.capture=capture;await capture.start();if(!current()){await capture.stop();throw Error('Start cancelled');}
          }
          if(this.system)this.system.start(this.plan.systemLocale,this.sessionId,this.plan.terms);
          if(!current())throw Error('Start cancelled');this.setState('listening');return this.diagnostics();
        }catch(error){if(current())await this.fail(error);throw error;}
      })();this.startTask=job;job.finally(()=>{if(this.startTask===job)this.startTask=null;}).catch(()=>{});return job;
    }
    beginEngine(offsetMs){this.engine.begin({sessionId:this.sessionId,segmentBase:this.segmentBase,offsetMs,pauseSeconds:this.options.pauseSeconds,maxSegmentSeconds:this.options.maxSegmentSeconds,threshold:.006});}
    write(samples,sampleRate,hints){if(this.input!=='pcm')return Promise.reject(Error('write requires start({input:"pcm"})'));return this.accept(samples,sampleRate,hints);}
    async accept(samples,rate,hints={}){
      const acceptingEpoch=this.epoch;
      if(!hints||typeof hints!=='object'||Array.isArray(hints))throw Error('Audio hints must be an object');
      const pendingPackets=hints.pendingPackets===undefined?0:hints.pendingPackets;
      if(!Number.isSafeInteger(pendingPackets)||pendingPackets<0||pendingPackets>150)throw Error('pendingPackets must be an integer from 0 to 150');
      if(!['starting','listening','recovering'].includes(this.state)&&!(this.state==='stopping'&&this.flushing))throw Error('Session is not accepting audio');
      if(!(samples instanceof Float32Array)||!samples.length||!Number.isFinite(rate)||rate<8000||rate>96000||samples.length>rate)throw Error('Expected 1..1000 ms Float32 PCM at 8000..96000 Hz');
      for(const sample of samples)if(!Number.isFinite(sample)||Math.abs(sample)>1)throw Error('PCM must be finite and normalized to [-1,1]');
      if(this.rate&&this.rate!==rate)throw Error('Sample rate cannot change during a session');this.rate=rate;
      for(let pos=0;pos<samples.length;pos+=Math.round(rate/10)){
        if(acceptingEpoch!==this.epoch||(!['starting','listening','recovering'].includes(this.state)&&!(this.state==='stopping'&&this.flushing)))throw Error('Audio processing was interrupted');
        const packet=samples.slice(pos,pos+Math.round(rate/10)),duration=packet.length/rate*1000;let energy=0;for(const v of packet)energy+=v*v;
        const speech=Math.sqrt(energy/packet.length)>.006;const lost=this.buffer.lostMs;this.buffer.push(packet,rate,speech);
        if(this.buffer.lostMs>lost)this.emit('warning',{code:'audio-buffer-overflow',lostMs:this.buffer.lostMs,message:'Uncommitted audio exceeded the 30 second recovery buffer'});
        if(this.state==='recovering')continue;
        if(this.system){
          this.quietMs=speech?0:this.quietMs+duration;if(speech)this.speechSinceTextMs+=duration;
          if(this.quietMs>=this.options.pauseSeconds*1000)this.system.endPhrase();
          if(this.speechSinceTextMs>=8000){await this.recover(Error('Speech detected without system transcript'),'no-result');}
        }else if(this.engine){try{await this.engine.audio(packet.slice(),rate,this.sessionId,{pendingPackets});}catch(error){if(acceptingEpoch!==this.epoch)throw Error('Audio processing was interrupted');if(this.state==='stopping')throw error;await this.recover(error,error.code||'failure');}}
      }
    }
    result(data){
      if(data.type==='clear-partial'){this.emit('clear-partial',{sessionId:this.sessionId});return;}
      if(!this.sessionId||data.sessionId!==this.sessionId||!['partial','final','interrupted'].includes(data.type))return;
      const id=data.segmentId;this.segmentBase=Math.max(this.segmentBase,id||0);const key=this.sessionId+':'+id;
      if(this.finalized.has(key))return;this.speechSinceTextMs=0;
      const timingReliable=this.candidate?.engine==='local'&&Number.isFinite(data.endMs),backend=this.candidate?.key;
      const event={...data,backend,sessionId:this.sessionId,rawText:data.text||'',text:data.text||'',turnComplete:false,timingReliable};
      if(data.type==='final'){
        event.wordConfidence=assessWords(event.text,data.words);
        this.finalized.add(key);if(event.text){if(timingReliable)this.buffer.commit(data.endMs);else this.nativeOverlapMs=this.buffer.endMs;}
        event.replayPossibleOverlap=timingReliable&&this.nativeOverlapMs>0&&(!Number.isFinite(data.startMs)||data.startMs<this.nativeOverlapMs);
        event.quality=assessQuality({text:event.text,durationMs:(data.endMs||0)-(data.startMs||0),voicedMs:data.voicedMs||0,clippedRatio:data.clippedRatio||0});
        if(event.replayPossibleOverlap){event.quality.status='review';event.quality.flags.push('Recovered audio may overlap a system transcript');}
      }
      this.emit(data.type,event);
    }
    recover(error,reason='failure'){
      if(this.recovery)return this.recovery;if(!['listening','starting'].includes(this.state))return Promise.resolve();
      const epoch=this.epoch,previous=this.candidate?.key;this.setState('recovering');this.closeBackend();this.emit('clear-partial',{sessionId:this.sessionId});this.emit('warning',{code:'recovering',message:error.message,previous});
      const job=(async()=>{try{
        const started=Date.now();
        while(epoch===this.epoch&&this.state==='recovering'){
          await this.nextBackend(epoch,reason,error);if(epoch!==this.epoch||this.state!=='recovering')return;
          let cursor=this.buffer.snapshot()[0]?.startMs??this.buffer.endMs;this.beginEngine(cursor);
          try{
            while(epoch===this.epoch&&this.state==='recovering'){
              const batch=this.buffer.snapshot().filter(p=>p.startMs>=cursor-.01);if(!batch.length)break;
              for(let i=0;i<batch.length;i++){const p=batch[i];if(epoch!==this.epoch||this.state!=='recovering')return;if(Date.now()-started>90000)throw Error('Recovery timeout');await this.engine.audio(p.samples,p.rate,this.sessionId,{pendingPackets:Math.min(150,batch.length-i)});cursor=p.endMs;}
            }
            if(epoch===this.epoch&&this.state==='recovering'){this.speechSinceTextMs=0;this.setState('listening');this.emit('recovered',{previous,backend:this.candidate.key,lostMs:this.buffer.lostMs});}return;
          }catch(nextError){if(epoch!==this.epoch)return;this.closeBackend();error=nextError;reason=nextError.code||'failure';}
        }
      }catch(failure){if(epoch===this.epoch)await this.fail(failure);}})();
      this.recovery=job;job.finally(()=>{if(this.recovery===job)this.recovery=null;}).catch(()=>{});return job;
    }
    async fail(error){if(this.state==='disposed')return;++this.epoch;++this.startEpoch;this.closeBackend();this.setState('error');this.emit('error',{code:error.code||'recognition-failed',message:error.message,sessionId:this.sessionId,backend:this.candidate?.key,processing:error.processing,pendingAudio:error.pendingAudio,recoverableAudioMs:this.buffer.endMs-this.buffer.committedMs});const capture=this.capture;this.capture=null;await capture?.stop();}
    closeBackend(){++this.backendEpoch;this.engine?.close();this.engine=null;this.system?.dispose();this.system=null;}
    stop(){
      if(this.stopTask)return this.stopTask;if(this.state==='disposed'||this.state==='idle')return Promise.resolve(this.diagnostics());
      const was=this.state;++this.startEpoch;this.startTask=null;this.setState('stopping');
      const job=(async()=>{let failure;
        if(['preparing','recovering'].includes(was)){++this.epoch;this.closeBackend();}
        this.flushing=true;const capture=this.capture;this.capture=null;try{await capture?.stop();}catch(e){failure=e;}this.flushing=false;
        try{
          if(this.engine&&this.sessionId&&this.rate)await this.engine.end(this.sessionId,this.rate);
          if(this.system&&this.sessionId)await new Promise(resolve=>{const timer=setTimeout(()=>{this.system?.stopTimedOut();resolve();},2000);this.systemStopped=()=>{clearTimeout(timer);resolve();};this.system.stop();});
        }catch(e){failure=e;}
        ++this.epoch;this.closeBackend();this.systemStopped=null;
        if(failure)this.emit('error',{code:'stop-incomplete',message:failure.message,sessionId:this.sessionId});
        if(this.state!=='disposed')this.setState('idle');return this.diagnostics();
      })();this.stopTask=job;job.finally(()=>{if(this.stopTask===job)this.stopTask=null;}).catch(()=>{});return job;
    }
    dispose(){if(this.disposeTask)return this.disposeTask;if(this.state==='disposed')return Promise.resolve();this.disposing=true;this.disposeTask=Promise.resolve().then(async()=>{await this.stop();this.setState('disposed');this.listeners.clear();this.buffer.clear();});return this.disposeTask;}
    diagnostics(){return {version:'0.3.0',state:this.state,sessionId:this.sessionId||null,backend:this.candidate?.key||null,plan:this.plan,load:this.loadStats||null,bufferedMs:this.buffer.endMs-this.buffer.committedMs,lostMs:this.buffer.lostMs};}
    exportPendingAudio(){return this.buffer.snapshot();}
  }
  root.LocalSpeech=Object.freeze({version:'0.3.0',assessWords,create:options=>new SpeechClient(options)});
})(globalThis);

})();
