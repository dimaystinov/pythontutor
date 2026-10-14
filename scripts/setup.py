#!/usr/bin/env python3
"""Create local configuration without overwriting an existing deployment."""
from pathlib import Path
import os
import secrets

root = Path(__file__).resolve().parents[1]
destination = root / '.env'
if destination.exists():
    print('.env already exists; preserved without changes.')
else:
    text = (root / '.env.example').read_text(encoding='utf-8')
    text = text.replace('SECRET_KEY=\n', 'SECRET_KEY=' + secrets.token_hex(48) + '\n')
    text = text.replace('RUNNER_TOKEN=\n', 'RUNNER_TOKEN=' + secrets.token_hex(32) + '\n')
    fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as output:
        output.write(text)
    print('Created .env with independent random secrets (mode 0600).')
print('Next: docker build -f runner/Dockerfile.worker -t pythontutor-worker:local .')
print('Then: docker compose up --build -d')
