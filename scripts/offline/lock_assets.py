"""Publisher-only: pin model artifacts and create the browser import allowlist."""
import hashlib,json,urllib.request,concurrent.futures
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def read(url):
 with urllib.request.urlopen(url,timeout=120) as r:return r.read()
def meta(repo):return json.loads(read('https://huggingface.co/api/models/'+repo+'?blobs=true'))
models=[('qwen7b','mlc-ai/Qwen2.5-Coder-7B-Instruct-q4f16_1-MLC'),('whisper-tiny','Xenova/whisper-tiny')]
files=[]
for group,repo in models:
 d=meta(repo);revision=d['sha']
 print(group,revision,flush=True)
 for f in d['siblings']:
  name=f['rfilename']
  wanted=(name.endswith('.bin') or name in ['mlc-chat-config.json','ndarray-cache.json','tokenizer.json']) if group=='qwen7b' else (('/' not in name and name.endswith(('.json','.txt'))) or name in ['onnx/encoder_model_quantized.onnx','onnx/decoder_model_merged_quantized.onnx'])
  if not wanted:continue
  url=f'https://huggingface.co/{repo}/resolve/{revision}/{name}'
  files.append(dict(path=group+'/'+name,size=f['size'],sha256=f.get('lfs',{}).get('sha256'),source=url,group=group,cache=('webllm/config' if name=='mlc-chat-config.json' else 'webllm/model') if group=='qwen7b' else 'transformers-cache'))
libpath='web-llm-models/v0_2_84/base/Qwen2-7B-Instruct-q4f16_1_cs1k-webgpu.wasm'
commits=json.loads(read('https://api.github.com/repos/mlc-ai/binary-mlc-llm-libs/commits?path='+libpath+'&per_page=1'))
files.append(dict(path='qwen7b/model.wasm',source='https://raw.githubusercontent.com/mlc-ai/binary-mlc-llm-libs/'+commits[0]['sha']+'/'+libpath,group='qwen7b',cache='webllm/wasm'))
def complete(f):
 if not f.get('sha256'):
  data=read(f['source']);f.update(size=len(data),sha256=hashlib.sha256(data).hexdigest())
 return f
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:files=list(pool.map(complete,files))
packages=[]
# Each tar remains far below GitHub's 2 GiB asset limit; import works one part at a time.
for group in ['qwen7b','whisper-tiny']:
 batch=[];size=0;index=1
 for f in sorted([x for x in files if x['group']==group],key=lambda x:x['path']):
  padded=512+((f['size']+511)//512)*512
  if size+padded>1500_000_000 and batch:
   packages.append(dict(name=f'{group}-part-{index}.tar',group=group,files=batch));batch=[];size=0;index+=1
  batch.append(f['path']);size+=padded
 if batch:packages.append(dict(name=f'{group}-part-{index}.tar',group=group,files=batch))
lock=dict(version=1,release='v1.1.0',files=files,packages=packages)
(ROOT/'scripts/offline/assets.lock.json').write_text(json.dumps(lock,ensure_ascii=False,indent=2)+'\n')
public={**lock,'files':[{k:v for k,v in f.items() if k!='source'} for f in files]}
(ROOT/'tutorial/static/pwa/model-assets.json').write_text(json.dumps(public,ensure_ascii=False,indent=2)+'\n')
print(len(files),'files',sum(f['size'] for f in files),'bytes',[p['name'] for p in packages],flush=True)
