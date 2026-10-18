import {loadPyodide} from '../vendor/pyodide/pyodide.mjs';
const base = new URL('../vendor/pyodide/', import.meta.url).href;
self.onmessage = async ({data: job}) => {
  try {
    self.postMessage({phase:'loading'});
    const py = await loadPyodide({indexURL:base});
    const engine = await (await fetch(new URL('engine.zip',import.meta.url))).arrayBuffer();
    py.unpackArchive(engine,'zip',{extractDir:'/home/pyodide'});
    if(job.image || /\b(cv2|numpy|PIL)\b/.test(job.code) || job.tests?.some(t=>t.image)) await py.loadPackage(['numpy','pillow','opencv-python']);
    py.runPython(`
import json, os, tempfile, base64, io
from evaldontevil.execplainator import exec as trace_exec, simple_exec

def browser_run(code, stdin, explain, image, expected, answer):
    with tempfile.TemporaryDirectory() as directory:
        before=os.getcwd()
        os.chdir(directory)
        try:
            if image:
                from PIL import Image
                raw=base64.b64decode(image)
                if len(raw)>2097152: raise ValueError('Изображение превышает 2 МиБ')
                with Image.open(io.BytesIO(raw)) as source:
                    if source.width*source.height>4000000: raise ValueError('Слишком большое изображение')
                    source.convert('RGB').save('input.png')
            result=(trace_exec if explain and not image else simple_exec)(code,stdin)
            if not image and isinstance(answer, str) and result['result']=='ok':
                actual_tokens=result.get('stdout','').split()
                expected_tokens=answer.split()
                def equal(a,b):
                    try: return abs(float(a)-float(b)) < 1e-3
                    except ValueError: return a==b
                if len(actual_tokens)!=len(expected_tokens) or not all(equal(a,b) for a,b in zip(actual_tokens,expected_tokens)):
                    result['result']='wrong_answer'
            if image and result['result']=='ok':
                from PIL import Image
                if not os.path.isfile('output.png') or os.path.getsize('output.png')>2097152:
                    result.update(result='invalid_image',stderr='Сохраните изображение в output.png (до 2 МиБ).')
                else:
                    with Image.open('output.png') as output:
                        if output.width*output.height>4000000: raise ValueError('Слишком большое изображение')
                        actual=output.convert('RGB')
                        if expected:
                            with Image.open(io.BytesIO(base64.b64decode(expected))) as target:
                                if actual.size!=target.size or actual.tobytes()!=target.convert('RGB').tobytes():
                                    result['result']='wrong_answer'
                        else:
                            png=io.BytesIO(); actual.save(png,format='PNG')
                            if png.tell()>2097152: raise ValueError('Результат превышает 2 МиБ')
                            result['image']=base64.b64encode(png.getvalue()).decode()
            return json.dumps(result,ensure_ascii=True,allow_nan=False)
        finally:
            os.chdir(before)
`);
    // Packages are fully loaded before student code runs. Static/native hosting
    // may not supply the worker CSP used by Django, so close these network APIs too.
    for (const name of ['fetch', 'XMLHttpRequest', 'WebSocket', 'EventSource', 'Worker', 'SharedWorker', 'importScripts']) {
      Object.defineProperty(self, name, {
        value: function () { throw new Error('Network access is disabled during Python execution.'); },
        writable: false, configurable: false
      });
    }
    const run = py.globals.get('browser_run');
    const inputs=job.tests || [{stdin:job.stdin||'',image:job.image}];
    const results=[];
    for(let i=0;i<inputs.length;i++) {
      self.postMessage({phase:'executing',index:i,total:inputs.length});
      const test=inputs[i];
      const result=JSON.parse(run(job.code,test.stdin||'',!!job.explain,test.image||'',test.expected||'',test.answer===undefined?null:test.answer));
      results.push(result);
      if(['output_limited','instructions_limited'].includes(result.result)) {
        while(results.length<inputs.length)results.push({result:'skipped',stdout:''});
        break;
      }
    }
    self.postMessage({result:job.tests?results:results[0]});
  } catch(error) {
    self.postMessage({error:String(error.message||error).slice(0,2000)});
  }
};
