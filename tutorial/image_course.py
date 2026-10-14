"""Trusted on-disk catalog and strict image boundaries for the OpenCV course."""
import base64
import io
import json
import warnings
from pathlib import Path
from django.conf import settings
from PIL import Image, UnidentifiedImageError

MAX_BYTES = 2 * 1024 * 1024
MAX_PIXELS = 4_000_000


def catalog():
    path = Path(settings.BASE_DIR) / 'image_course' / 'catalog.json'
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding='utf-8'))
    return data['tasks'] if isinstance(data, dict) else data


def material_path(relative):
    root = (Path(settings.BASE_DIR) / 'image_course').resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError('Invalid course asset path')
    return path


def canonical_image(data):
    if len(data) > MAX_BYTES:
        raise ValueError('Изображение должно быть не больше 2 МиБ.')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as source:
                if source.format not in ('PNG', 'JPEG') or source.width * source.height > MAX_PIXELS:
                    raise ValueError('Нужен PNG/JPEG не больше 4 миллионов пикселей.')
                source.load()
                image = source.convert('RGB')
                output = io.BytesIO()
                image.save(output, format='PNG')
    except (UnidentifiedImageError, OSError, Image.DecompressionBombWarning, Image.DecompressionBombError) as exc:
        raise ValueError('Не удалось прочитать PNG/JPEG.') from exc
    result = output.getvalue()
    if len(result) > MAX_BYTES:
        raise ValueError('Изображение после преобразования превышает 2 МиБ. Уменьшите его.')
    return result


def image_matches(encoded, expected):
    if not encoded or len(encoded) > MAX_BYTES * 2:
        return False
    try:
        actual_bytes = canonical_image(base64.b64decode(encoded, validate=True))
        expected_bytes = canonical_image(expected)
        with Image.open(io.BytesIO(actual_bytes)) as actual, Image.open(io.BytesIO(expected_bytes)) as target:
            return actual.size == target.size and actual.tobytes() == target.tobytes()
    except (ValueError, TypeError):
        return False
