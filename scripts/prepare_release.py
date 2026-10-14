#!/usr/bin/env python3
"""Prepare a clean first-publication snapshot, never copy credentials or Git history."""
import argparse, hashlib, json, shutil, subprocess, zipfile
parser=argparse.ArgumentParser()
parser.add_argument("--snapshot-only", action="store_true")
parser.add_argument('--version', default='v1.1.0')
args=parser.parse_args()
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'dist/release-source'
out.mkdir(parents=True,exist_ok=True)
paths=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=ROOT).decode().split('\0')
for name in paths:
 if not name:continue
 p=Path(name)
 if not (ROOT/p).is_file() or (ROOT/p).is_symlink():continue
 if any(part in {'.git','.private','node_modules','data','backups','.venv','.venv314','dist','__pycache__'} for part in p.parts):continue
 if p.name.startswith('.env') and p.name!='.env.example':continue
 if p.parts[:2]==('docs','superpowers') or (p.parts[0]=='docs' and p.suffix in {'.png','.jpg'}):continue
 target=out/p;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/p,target)
if args.snapshot_only:
 print(out)
 raise SystemExit(0)
assets=ROOT/'dist/releases';assets.mkdir(exist_ok=True)
for folder,name in [(out,f'pythontutor-source-{args.version}.zip'),(ROOT/'dist/pages',f'pythontutor-pages-{args.version}.zip')]:
 with zipfile.ZipFile(assets/name,'w',zipfile.ZIP_DEFLATED) as z:
  for p in sorted(folder.rglob('*')):
   if p.is_file() and '.git' not in p.parts and not (folder.name=='pages' and 'audit' in p.relative_to(folder).parts[0]):z.write(p,p.relative_to(folder))
files=sorted(assets.glob('*'+args.version+'.zip'))
(assets/'SHA256SUMS.txt').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in files))
print(out)
for p in files:print(p.name,p.stat().st_size)
