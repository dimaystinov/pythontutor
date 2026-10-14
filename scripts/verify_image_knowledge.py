#!/usr/bin/env python3
"""Check our trusted image editorials against exact fixture pixels."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from PIL import Image
import numpy as np

root=Path(__file__).resolve().parents[1]
checks=0
for task in json.loads((root/'image_course/catalog.json').read_text()):
    article=json.loads((root/'knowledge/images'/(task['slug']+'.json')).read_text())
    for variant in [article['recommended']]+article['alternatives']:
        for case in task['tests']:
            with tempfile.TemporaryDirectory() as work:
                shutil.copy(root/'image_course'/case['input'],Path(work)/'input.png')
                result=subprocess.run([sys.executable,'-I','-c',variant['code']],cwd=work,capture_output=True,text=True,timeout=10)
                assert result.returncode==0,(task['slug'],result.stderr)
                with Image.open(Path(work)/'output.png') as output, Image.open(root/'image_course'/case['expected']) as expected:
                    assert np.array_equal(np.asarray(output),np.asarray(expected)),(task['slug'],variant['title'],case)
                checks+=1
    print('PASS',task['slug'],flush=True)
print(f'{checks} exact image comparisons passed.')
