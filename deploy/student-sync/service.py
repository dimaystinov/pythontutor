"""Loopback-only progress service; nginx terminates TLS and rate-limits requests."""
import admin
import hashlib,hmac,json,re,sqlite3,secrets,os
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from contextlib import closing
DB=os.environ.get('SYNC_DB','/var/lib/pythontutor-sync/progress.db')
def handle(msg):
    if msg.get('op')=='journal':
        key=os.environ.get('PT_JOURNAL_KEY','')
        if not key or not hmac.compare_digest(key.encode(),str(msg.get('key','')).encode()):return 403,{}
        if msg.get('action'):
            with closing(sqlite3.connect(DB,timeout=8)) as db,db:return 200,admin.dashboard(db,msg)
        ids=msg.get('ids')
        if not isinstance(ids,list) or len(ids)>500 or not all(isinstance(x,str) and re.fullmatch('[a-f0-9]{64}',x) for x in ids):raise ValueError()
        result={}
        with closing(sqlite3.connect(DB,timeout=8)) as db:
            for uid,items in db.execute('SELECT id,items FROM accounts WHERE id IN ('+','.join('?' for _ in ids)+')',ids):
                result[uid]=[{k:r[k] for k in ('kind','slug','solved','time')} for r in json.loads(items).values()]
        return 200,{'students':result}
    uid,token=msg['id'],msg['proof']
    if not all(isinstance(x,str) and re.fullmatch('[a-f0-9]{64}',x) for x in (uid,token)):raise ValueError()
    op=msg['op']
    if op not in ('login','sync'):raise ValueError()
    with closing(sqlite3.connect(DB,timeout=8)) as db,db:
        db.execute('BEGIN IMMEDIATE')
        row=db.execute('SELECT salt,proof,epoch,items FROM accounts WHERE id=?',(uid,)).fetchone()
        if row is None and op!='login':return 403,{}
        salt=row[0] if row else secrets.token_bytes(24)
        proof=hashlib.sha256(salt+bytes.fromhex(token)).digest()
        if row and not hmac.compare_digest(row[1],proof):return 403,{}
        epoch,items=(row[2],json.loads(row[3])) if row else (0,{})
        if op=='sync' and msg['epoch']==epoch:
            if msg.get('reset') is True:epoch+=1;items={}
            incoming=msg['items']
            if not isinstance(incoming,list) or len(incoming)>300:raise ValueError()
            for entry in incoming:
                k,s,t=entry['kind'],entry['slug'],entry['time']
                if k not in ('image','problem') or not re.fullmatch('[a-zA-Z0-9_-]{1,150}',s) or not re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z',t):raise ValueError()
                if type(entry['solved']) is not bool:raise ValueError()
                key=k+':'+s;old=items.get(key)
                clean={f:entry[f] for f in ('kind','slug','time','solved','code','acceptedCode')}
                if any(not isinstance(clean[f],str) or len(clean[f])>100000 for f in ('code','acceptedCode')):raise ValueError()
                admin.record(db,uid,clean)
                if old:
                    newer,older=(old,clean) if old['time']>t else (clean,old)
                    clean={**newer,'solved':old['solved'] or clean['solved'],'acceptedCode':newer['acceptedCode'] or older['acceptedCode']}
                items[key]=clean
        encoded=json.dumps(items,ensure_ascii=False,separators=(',',':'))
        if len(items)>300 or len(encoded.encode())>3_000_000:raise ValueError()
        db.execute('INSERT OR REPLACE INTO accounts VALUES(?,?,?,?,?)',(uid,salt,proof,epoch,encoded))
        return 200,{'epoch':epoch,'items':list(items.values())}
class Api(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            if self.path not in ('/progress','/journal'):return self.send_error(404)
            n=int(self.headers.get('Content-Length','0'))
            if not 0<n<=4_000_000:return self.send_error(413)
            msg=json.loads(self.rfile.read(n))
            if not isinstance(msg,dict):raise ValueError()
            if (self.path=='/journal') != (msg.get('op')=='journal'):
                status,data=403,{}
            else:
                status,data=handle(msg)
        except (KeyError,TypeError,ValueError):status,data=400,{}
        except sqlite3.Error:status,data=503,{}
        body=json.dumps(data,ensure_ascii=False).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    def log_message(self,*args):pass
if __name__=='__main__':
    with sqlite3.connect(DB) as db:db.execute('CREATE TABLE IF NOT EXISTS accounts(id TEXT PRIMARY KEY,salt BLOB,proof BLOB,epoch INTEGER,items TEXT)')
    with sqlite3.connect(DB) as db:admin.initialize(db)
    ThreadingHTTPServer(('127.0.0.1',18442),Api).serve_forever()
