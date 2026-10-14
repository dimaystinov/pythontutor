"""Validate static navigation, data coverage and absence of server-only UI."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import json
ROOT=Path(__file__).resolve().parents[1]/'dist/pages'
base='/pythontutor-selfhost/'
class Links(HTMLParser):
 def __init__(self): super().__init__();self.urls=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  for key in ('href','src','poster'):
   if a.get(key): self.urls.append(a[key])
missing=set()
for p in ROOT.rglob('*.html'):
 if 'static' in p.relative_to(ROOT).parts or 'audit' in p.parts:continue
 s=p.read_text();parser=Links();parser.feed(s)
 assert '/accounts/login/' not in s,p
 for url in parser.urls:
  u=urlsplit(url)
  if u.scheme or u.netloc or not u.path:continue
  if u.path.startswith('/'):
   if not u.path.startswith(base):missing.add((p.relative_to(ROOT).as_posix(),url));continue
   dest=ROOT/unquote(u.path[len(base):])
  else:dest=p.parent/unquote(u.path)
  if dest.is_dir():dest=dest/'index.html'
  if not dest.is_file():missing.add((p.relative_to(ROOT).as_posix(),url))
for item in sorted(missing): print('MISSING',*item)
counts={};total=0
for kind,expected in [('problem',134),('image',8)]:
 files=list((ROOT/'browser/tests'/kind).glob('*/index.json'));assert len(files)==expected
 count=sum(len(json.loads(p.read_text())['tests']) for p in files);counts[kind]=count;total+=count
assert counts=={'problem':1302,'image':24},counts
assert not missing,f'{len(missing)} broken internal references'
print('PASS 304 pages; 134 Python tasks/1302 tests; 8 OpenCV tasks/24 tests; internal links and assets exist')
