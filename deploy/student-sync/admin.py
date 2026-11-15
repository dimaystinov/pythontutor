"""Teacher-only operations. Called after the journal key and client certificate checks."""
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import re

MOSCOW = timezone(timedelta(hours=3))

def day_of(timestamp):
    return datetime.fromisoformat(timestamp.replace('Z', '+00:00')).astimezone(MOSCOW).date().isoformat()

def initialize(db):
    db.execute('CREATE TABLE IF NOT EXISTS attendance(member TEXT,grp TEXT,day TEXT,PRIMARY KEY(member,grp,day))')
    db.execute('CREATE TABLE IF NOT EXISTS activity(uid TEXT,day TEXT,kind TEXT,slug TEXT,PRIMARY KEY(uid,day,kind,slug))')
    if db.execute('PRAGMA user_version').fetchone()[0] == 0:
        for uid,items in db.execute('SELECT id,items FROM accounts'):
            for item in json.loads(items).values():
                record(db,uid,item)
        db.execute('PRAGMA user_version=1')

def record(db,uid,item):
    db.execute('INSERT OR IGNORE INTO activity VALUES (?,?,?,?)',(uid,day_of(item['time']),item['kind'],item['slug']))

def dashboard(db,msg):
    action=msg.get('action')
    if action=='roster':
        return json.loads(Path('/opt/pythontutor-sync/roster.enc.json').read_text())
    day=date.fromisoformat(msg['day']).isoformat()
    if action=='attendance':
        member=msg['member']
        group=msg['group']
        if not re.fullmatch('[a-f0-9]{64}',member) or group not in ('1','2','3') or type(msg['present']) is not bool:raise ValueError()
        if msg['present']:
            db.execute('INSERT OR IGNORE INTO attendance VALUES(?,?,?)',(member,group,day))
        else:
            db.execute('DELETE FROM attendance WHERE member=? AND grp=? AND day=?',(member,group,day))
        return {'saved':True}
    if action!='overview':raise ValueError()
    ids=msg['ids']
    if not isinstance(ids,list) or len(ids)>900 or not all(isinstance(i,str) and re.fullmatch('[a-f0-9]{64}',i) for i in ids):raise ValueError()
    placeholders=','.join('?' for i in ids)
    students={}
    for uid,data in db.execute('SELECT id,items FROM accounts WHERE id IN ('+placeholders+')',ids):
        items=json.loads(data)
        students[uid]={'solved':sum(r['solved'] for r in items.values()),'started':sum(not r['solved'] for r in items.values()),'tasks':[]}
    for uid,kind,slug in db.execute('SELECT uid,kind,slug FROM activity WHERE day=? AND uid IN ('+placeholders+') ORDER BY kind,slug',[day,*ids]):
        if uid in students:students[uid]['tasks'].append(kind+':'+slug)
    return {'students':students,'attendance':[list(r) for r in db.execute('SELECT member,grp FROM attendance WHERE day=?',(day,))]}
