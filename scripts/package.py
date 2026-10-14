#!/usr/bin/env python3
"""Build a portable source archive, excluding secrets, users and local runtimes."""
import hashlib
import os
from pathlib import Path
import tarfile

root = Path(__file__).resolve().parents[1]
target = root.parent / 'pythontutor-selfhost.tar.gz'
excluded = {'.git', '.venv', '.venv314', 'venv', '__pycache__', '.pytest_cache',
            'node_modules', '.private', 'data', 'backups', 'collected_static', 'dist', '.superpowers'}
with tarfile.open(target, 'w:gz') as archive:
    for directory, directories, files in os.walk(root):
        directories[:] = sorted(d for d in directories if d not in excluded)
        for name in sorted(files):
            path = Path(directory) / name
            if name == '.env' or (name.startswith('.env.') and name != '.env.example'):
                continue
            if path.suffix in ('.pyc', '.sqlite3') or path.is_symlink():
                continue
            archive.add(path, arcname=str(Path(root.name) / path.relative_to(root)), recursive=False)
with tarfile.open(target) as archive:
    names = archive.getnames()
    assert not any(set(Path(name).parts) & excluded for name in names)
    assert not any(Path(name).name == '.env' for name in names)
    assert 'pythontutor-selfhost/example.db' in names
    assert 'pythontutor-selfhost/image_course/catalog.json' in names
    assert 'pythontutor-selfhost/scripts/start.sh' in names
digest = hashlib.sha256(target.read_bytes()).hexdigest()
target.with_suffix(target.suffix + '.sha256').write_text(digest + '  ' + target.name + '\n')
print(f'{target}\n{len(names)} files, {target.stat().st_size:,} bytes\nSHA256 {digest}')
