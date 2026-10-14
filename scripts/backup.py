#!/usr/bin/env python3
"""Consistent SQLite backup from the running Compose web service."""
from datetime import datetime, timezone
from pathlib import Path
import os
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
directory = root / 'backups'
directory.mkdir(mode=0o700, exist_ok=True)
target = directory / (datetime.now(timezone.utc).strftime('pythontutor-%Y%m%dT%H%M%SZ') + '.sqlite3')
code = '''import os, sqlite3, sys, tempfile
with tempfile.TemporaryDirectory() as directory:
    path = directory + '/backup.sqlite3'
    source = sqlite3.connect(os.environ['DATABASE_PATH'])
    destination = sqlite3.connect(path)
    with destination:
        source.backup(destination)
    destination.close()
    source.close()
    with open(path, 'rb') as backup:
        sys.stdout.buffer.write(backup.read())
'''
fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
try:
    with os.fdopen(fd, 'wb') as output:
        subprocess.run(['docker', 'compose', 'exec', '-T', 'web', 'python', '-c', code],
                       cwd=root, stdout=output, check=True)
except BaseException:
    target.unlink(missing_ok=True)
    raise
print(target)
