#!/usr/bin/env python3
"""Reproduce original synthetic OpenCV teaching fixtures and expected PNGs.

Run with the pinned worker requirements. All images are procedural educational
test data created for this project; no downloaded photographs are used.
"""
from pathlib import Path
import hashlib
import json
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1] / 'image_course'
PREFIX = "import cv2\nimport numpy as np\n\nimage = cv2.imread('input.png')\n"
SUFFIX = "\ncv2.imwrite('output.png', result)\n"
TASKS = [
    ('grayscale', 'Оттенки серого',
     'Прочитайте input.png через cv2.imread и переведите изображение из BGR в оттенки серого с помощью cv2.COLOR_BGR2GRAY. Сохраните результат в output.png без изменения размеров.',
     'result = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)'),
    ('negative', 'Негатив изображения',
     'Создайте цветной негатив: замените каждое значение каждого канала v на 255 − v. Сохраните размеры и запишите результат в output.png.',
     'result = cv2.bitwise_not(image)'),
    ('resize', 'Уменьшение вдвое',
     'Уменьшите ширину и высоту изображения вдвое с округлением вниз. Используйте cv2.resize с интерполяцией cv2.INTER_NEAREST. Запишите результат в output.png.',
     'height, width = image.shape[:2]\nresult = cv2.resize(image, (width // 2, height // 2), interpolation=cv2.INTER_NEAREST)'),
    ('rotate', 'Поворот на 90°',
     'Поверните цветное изображение на 90 градусов по часовой стрелке. Используйте cv2.rotate и cv2.ROTATE_90_CLOCKWISE. Сохраните результат в output.png.',
     'result = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)'),
    ('threshold', 'Пороговая обработка',
     'Сначала переведите BGR-изображение в оттенки серого через cv2.COLOR_BGR2GRAY. Примените cv2.threshold с порогом 127, максимумом 255 и типом cv2.THRESH_BINARY: значения строго больше 127 становятся 255, остальные — 0. Сохраните output.png.',
     'gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)\n_, result = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)'),
    ('blur', 'Гауссово размытие',
     'Примените к цветному изображению cv2.GaussianBlur с ядром (5, 5), sigmaX=0 и borderType=cv2.BORDER_DEFAULT. Сохраните output.png, сохранив размеры и три канала.',
     'result = cv2.GaussianBlur(image, (5, 5), 0, borderType=cv2.BORDER_DEFAULT)'),
    ('edges', 'Границы Canny',
     'Переведите BGR-изображение в серое через cv2.COLOR_BGR2GRAY. Найдите границы cv2.Canny с threshold1=100, threshold2=200, apertureSize=3, L2gradient=False. Сохраните одноканальное изображение границ в output.png.',
     'gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)\nresult = cv2.Canny(gray, 100, 200, apertureSize=3, L2gradient=False)'),
    ('crop', 'Центральный фрагмент',
     'Используйте срез NumPy, чтобы вырезать центральный фрагмент: строки от height // 4 включительно до 3 * height // 4 не включительно, столбцы от width // 4 включительно до 3 * width // 4 не включительно. Сохраните цветной фрагмент в output.png.',
     'height, width = image.shape[:2]\nresult = image[height // 4:3 * height // 4, width // 4:3 * width // 4]'),
]


def fixture(width, height, seed):
    y, x = np.mgrid[:height, :width]
    image = np.stack(((x * 3 + y + seed * 19) % 256,
                      (x + y * 2 + seed * 53) % 256,
                      (x * 2 + y * 3 + seed * 31) % 256), axis=2).astype(np.uint8)
    cv2.rectangle(image, (width // 12, height // 7), (width // 2, height * 3 // 5), (220, 40, 20), -1)
    cv2.circle(image, (width * 3 // 4, height // 2), min(width, height) // 5, (40, 220, 240), -1)
    cv2.line(image, (0, height - 1), (width - 1, 0), (255, 255, 255), 3)
    cv2.putText(image, 'PY', (width // 8, height * 4 // 5), cv2.FONT_HERSHEY_SIMPLEX, .65, (10, 15, 25), 2)
    return image


def main():
    (ROOT / 'fixtures').mkdir(parents=True, exist_ok=True)
    (ROOT / 'expected').mkdir(exist_ok=True)
    fixtures = [fixture(w, h, i) for i, (w, h) in enumerate(((256, 192), (160, 120), (127, 95)))]
    for index, image in enumerate(fixtures):
        assert cv2.imwrite(str(ROOT / 'fixtures' / f'input-{index}.png'), image)
    catalog = []
    for slug, title, statement, implementation in TASKS:
        tests = []
        for index, image in enumerate(fixtures):
            # Only fixed project-owned reference code is executed by this generator.
            namespace = {'cv2': cv2, 'np': np, 'image': image.copy()}
            exec(implementation, namespace)
            expected = f'expected/{slug}-{index}.png'
            assert cv2.imwrite(str(ROOT / expected), namespace['result'])
            tests.append({'input': f'fixtures/input-{index}.png', 'expected': expected})
        catalog.append({'slug': slug, 'title': title, 'statement': statement,
                        'starter': PREFIX + '\n# Напишите обработку изображения здесь\nresult = image.copy()' + SUFFIX,
                        'solution': PREFIX + implementation + SUFFIX, 'tests': tests})
    (ROOT / 'catalog.json').write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    manifest = {'opencv': cv2.__version__, 'numpy': np.__version__, 'tasks': len(catalog),
                'checks': sum(len(t['tests']) for t in catalog),
                'sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in sorted(ROOT.rglob('*.png'))}}
    (ROOT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'Generated {len(catalog)} image tasks and {manifest["checks"]} checks with OpenCV {cv2.__version__}.')


if __name__ == '__main__':
    main()
