#!/usr/bin/env python3
"""Verify our authored reference programs, never arbitrary learner submissions.
Runs local trusted source with isolated Python against all archived test pairs.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--workers', type=int, default=4)
parser.add_argument('--report', type=Path, default=root/'knowledge/verification.json')
args = parser.parse_args()
problems = json.loads((root/'knowledge/problems.json').read_text())

def matches(actual, expected):
    a,b=actual.split(),expected.split()
    if len(a)!=len(b): return False
    for x,y in zip(a,b):
        try: same=abs(float(x)-float(y))<1e-3
        except ValueError: same=x==y
        if not same: return False
    return True

def verify(problem):
    path=root/'knowledge/solutions'/(problem['urlname']+'.json')
    if not path.exists(): return {'slug':problem['urlname'],'error':'Missing article'}
    data=json.loads(path.read_text())
    if data.get('slug')!=problem['urlname'] or not data.get('alternatives'): return {'slug':problem['urlname'],'error':'Invalid schema or no alternative'}
    count=0
    for variant in [data['recommended']]+data['alternatives']:
        for key in ['title','code','explanation','time_complexity','space_complexity']:
            if not variant.get(key): return {'slug':problem['urlname'],'error':'Missing '+key}
        for i,(stdin,expected) in enumerate(zip(problem['tests'],problem['answers'])):
            try:
                process=subprocess.run([sys.executable,'-I','-c',variant['code']],input=stdin+'\n',text=True,capture_output=True,timeout=5)
            except subprocess.TimeoutExpired:
                return {'slug':problem['urlname'],'variant':variant['title'],'test':i+1,'error':'Timeout'}
            if process.returncode or not matches(process.stdout,expected):
                return {'slug':problem['urlname'],'variant':variant['title'],'test':i+1,'error':process.stderr or 'Wrong answer','actual':process.stdout[:1000],'expected':expected[:1000]}
            count+=1
    return {'slug':problem['urlname'],'variants':1+len(data['alternatives']),'checks':count,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}

with ThreadPoolExecutor(max_workers=args.workers) as executor:
    results=list(executor.map(verify,problems))
report={'python':sys.version.split()[0],'problems':len(results),'checks':sum(x.get('checks',0) for x in results),'variants':sum(x.get('variants',0) for x in results),'failures':[x for x in results if 'error' in x],'results':results}
args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='results'},ensure_ascii=False,indent=2))
sys.exit(bool(report['failures']))
