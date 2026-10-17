const {test}=require('node:test');
const assert=require('node:assert/strict');
test('native inference reads one disk store without browser or HTTP caching',async()=>{
 const {NativeFileCache}=await import('../vendor/webllm/native-file-cache.mjs');
 const original=global.fetch;const calls=[];
 global.fetch=async(url,options)=>{calls.push({url,options});return new Response('{"ok":true}');};
 try{
  const cache=new NativeFileCache();const url='asset://localhost/models/qwen7b/mlc-chat-config.json';
  assert.deepEqual(await cache.fetchWithCache(url,'json'),{ok:true});
  assert.equal(calls[0].options.cache,'no-store');
  await cache.addToCache(url);await cache.deleteInCache(url);
  assert.equal(await cache.hasAllKeys([url]),true);
  assert.equal(calls.length,1);
  await assert.rejects(cache.fetchWithCache('https://example.org/model.bin','arraybuffer'));
  await assert.rejects(cache.hasAllKeys(['http://evil.test/file']));
  assert.equal(calls.length,1);
 }finally{global.fetch=original;}
});
