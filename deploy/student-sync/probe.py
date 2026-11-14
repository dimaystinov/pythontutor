"""Exercise the deployed service using synthetic accounts only."""
import json,secrets,ssl,urllib.request,urllib.error,sys
ctx=ssl.create_default_context(cafile=sys.argv[1])
uid,token,other=[secrets.token_hex(32) for _ in range(3)]
def req(op,expected=200,**kw):
    data=dict(id=uid,proof=token,op=op);data.update(kw)
    try:
        with urllib.request.urlopen(urllib.request.Request('https://109.196.164.69:8443/progress',data=json.dumps(data).encode(),headers={'Content-Type':'application/json'}),context=ctx,timeout=10) as r:
            assert r.status==expected;return json.load(r)
    except urllib.error.HTTPError as e:assert e.code==expected,(e.code,expected)
assert req('login')['items']==[]
x=dict(kind='problem',slug='vertex_degrees',time='2026-11-14T10:00:00.000Z',solved=False,code='print(0)',acceptedCode='')
assert req('sync',epoch=0,items=[x])['items']==[x]
y={**x,'time':'2026-11-14T10:01:00.000Z','solved':True,'code':'print(1)','acceptedCode':'print(1)'}
assert req('sync',epoch=0,items=[y])['items']==[y]
assert req('sync',epoch=0,items=[x])['items']==[y]
assert req('login')['items']==[y]
req('login',403,proof=other)
assert req('login',id=other)['items']==[]
assert req('sync',epoch=0,items=[],reset=True)=={'epoch':1,'items':[]}
assert req('sync',epoch=0,items=[y])=={'epoch':1,'items':[]}
print('PASS HTTPS: save, update, restore, stale write, wrong password, isolation, reset')
print(uid,other)
