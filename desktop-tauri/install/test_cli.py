"""Isolated tests: no changes to the user's shell configuration."""
import os
import pathlib
import subprocess
import tempfile

script = pathlib.Path(__file__).with_name('install-cli.sh').resolve()
with tempfile.TemporaryDirectory(prefix='tutor cli ') as directory:
    home = pathlib.Path(directory) / 'home'
    home.mkdir()
    source = pathlib.Path(directory) / 'opencode'
    source.write_text('#!/bin/sh\nprintf "test-opencode\\n"\n')
    source.chmod(0o755)
    (home / '.zshrc').write_text('export KEEP_USER_SETTING=yes\n')
    for _ in range(2):
        subprocess.run(['/bin/sh', str(script), str(source), str(home)], check=True)
    profile = (home / '.zshrc').read_text()
    assert profile.count('# PythonTutor OpenCode CLI') == 1
    assert 'KEEP_USER_SETTING=yes' in profile
    env = {**os.environ, 'HOME': str(home), 'ZDOTDIR': str(home), 'PATH': '/usr/bin:/bin'}
    for shell, args in [('/bin/zsh', ['-ic', 'opencode']),
                        ('/bin/bash', ['--noprofile', '-c', '. "$HOME/.bashrc"; opencode'])]:
        result = subprocess.run([shell, *args], env=env, capture_output=True, text=True, check=True)
        assert result.stdout.strip() == 'test-opencode', result.stdout
    source.write_text('#!/bin/sh\nprintf "updated-opencode\\n"\n')
    subprocess.run(['/bin/sh', str(script), str(source), str(home)], check=True)
    result = subprocess.check_output([str(home / '.local/share/pythontutor/bin/opencode')], text=True)
    assert result.strip() == 'updated-opencode'
print('PASS: zsh/bash lookup, spaces, idempotence, profile preservation, CLI update')
