"""Initialize persistent schema/content, then replace this process with WSGI."""
import os
import subprocess
import sys

for command in (['migrate', '--noinput'], ['seed_course']):
    subprocess.run([sys.executable, 'manage.py', *command], check=True)
os.execvp(sys.argv[1], sys.argv[1:])
