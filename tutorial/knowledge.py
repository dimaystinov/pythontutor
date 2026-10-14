"""Local, reviewed editorials; never expose solution files through static URLs."""
import json
from pathlib import Path
from django.conf import settings
from tutorial.models import Submission, ImageSubmission


def article(slug, image=False):
    root = Path(settings.BASE_DIR) / 'knowledge' / ('images' if image else 'solutions')
    path = root / (slug + '.json')
    if path.parent != root or not path.is_file():
        return None
    data = json.loads(path.read_text(encoding='utf-8'))
    return data if data.get('slug') == slug else None


def solved(user, problem=None, image_slug=None):
    if not user.is_authenticated:
        return False
    if image_slug is not None:
        return ImageSubmission.objects.filter(user=user, task_slug=image_slug, status='ok').exists()
    return Submission.objects.filter(user=user, problem=problem, status__in=[1, 2]).exists()
