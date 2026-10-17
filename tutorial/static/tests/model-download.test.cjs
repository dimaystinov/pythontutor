const {test}=require('node:test'),assert=require('node:assert/strict');
const {createHash}=require('node:crypto');
const asset=(path='qwen7b/a.bin',body=Buffer.from('abc'))=>({path,size:body.length,sha256:createHash('sha256').update(body).digest('hex'),source:'https://huggingface.co/test/'+path});
function zipEntry(path,body){const name=Buffer.from(path),header=Buffer.alloc(30);header.writeUInt32LE(0x04034b50);header.writeUInt32LE(body.length,18);header.writeUInt32LE(body.length,22);header.writeUInt16LE(name.length,26);return Buffer.concat([header,name,body]);}
test('stored ZIP streams across chunk boundaries and checks file checksums',async()=>{
 const {readStoredZip,checkedBytes}=await import('../pwa/model-download.mjs');const item=asset(),body=zipEntry(item.path,Buffer.from('abc'));let offset=0,saved=[];
 const stream=new ReadableStream({pull(c){if(offset>=body.length)return c.close();c.enqueue(body.subarray(offset,offset+7));offset+=7;}});
 await readStoredZip(stream.getReader(),[item],async(f,b)=>saved.push(await checkedBytes(b,f)),new AbortController().signal);
 assert.equal(Buffer.from(saved[0]).toString(),'abc');
 await assert.rejects(checkedBytes(Buffer.from('bad'),item));
 await assert.rejects(readStoredZip(new Response(zipEntry('../outside',Buffer.from('abc'))).body.getReader(),[item],async()=>{},new AbortController().signal));
});
test('browser falls back from blocked Yandex and corrupt server to verified HF bytes',async()=>{
 const {downloadModel}=await import('../pwa/model-download.mjs');const old=global.fetch,calls=[],saved=[];
 global.fetch=async(url)=>{calls.push(url);if(url.includes('/model-download/'))throw TypeError('Failed to fetch');return new Response(url.includes('duckdns')?'bad':'abc');};
 try{await downloadModel([asset()],{present:async()=>false,save:async(f,b)=>saved.push(Buffer.from(b).toString()),signal:new AbortController().signal});assert.deepEqual(saved,['abc']);assert.equal(calls.length,3);assert.ok(calls[2].includes('huggingface'));}finally{global.fetch=old;}
});
test('partial browser installation resumes only missing files and never downloads ZIP again',async()=>{
 const {downloadModel}=await import('../pwa/model-download.mjs');const old=global.fetch,calls=[];global.fetch=async url=>{calls.push(url);return new Response('abc');};
 try{await downloadModel([asset(),asset('qwen7b/b.bin')],{present:async a=>a.path.endsWith('/a.bin'),save:async()=>{},signal:new AbortController().signal});assert.equal(calls.length,1);assert.ok(calls[0].endsWith('/b.bin'));}finally{global.fetch=old;}
});
test('quota errors stop downloading instead of retrying the same file on other sources',async()=>{
 const {downloadModel}=await import('../pwa/model-download.mjs');const old=global.fetch,calls=[];global.fetch=async url=>{calls.push(url);if(url.includes('/model-download/'))throw TypeError('blocked');return new Response('abc');};
 try{await assert.rejects(downloadModel([asset()],{present:async()=>false,save:async()=>{throw new DOMException('full','QuotaExceededError');},signal:new AbortController().signal}),{name:'QuotaExceededError'});assert.equal(calls.length,2);}finally{global.fetch=old;}
});
