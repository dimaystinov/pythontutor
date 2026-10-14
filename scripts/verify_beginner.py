"""Check that lesson-one starters and editorials do not introduce later concepts."""
import ast
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tutorial.beginner import STARTERS
root = Path(__file__).resolve().parents[1]
assert len(STARTERS) == 5
for slug, (starter, example, _) in STARTERS.items():
    article = json.loads((root / 'knowledge/solutions' / (slug + '.json')).read_text())
    for code in [starter, example, article['recommended']['code']] + [a['code'] for a in article['alternatives']]:
        for node in ast.walk(ast.parse(code)):
            assert not isinstance(node, (ast.For, ast.While, ast.ListComp, ast.GeneratorExp, ast.Import, ast.ImportFrom, ast.JoinedStr)), (slug, type(node).__name__)
            if isinstance(node, ast.Call):
                assert isinstance(node.func, ast.Name) and node.func.id in {'input', 'int', 'print'}, (slug, ast.dump(node))
    print('PASS beginner:', slug)
