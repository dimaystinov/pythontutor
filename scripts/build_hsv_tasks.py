"""Reproducible teaching fixtures from the four supplied HSV photographs (OpenCV 4.11)."""
from pathlib import Path
import json
import cv2
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
COURSE=ROOT/'image_course'
# Thresholds are part of the specification: exact masks are reproducible, not subjective.
LESSONS=[
 ('hsv-blue','HSV: синий колпачок','img.jpg',[(100,100,50,140,255,255)],False,
  'Выделите синие участки колпачка маркера на фотографии стола.',
  ['cv2.imread возвращает BGR. Сначала переведите фотографию в HSV через cv2.COLOR_BGR2HSV.', 'cv2.inRange получает нижнюю и верхнюю границы сразу для трёх каналов. Результат уже является маской 0/255.']),
 ('hsv-moon','HSV: Луна на вечернем небе','moon.jpg',[(0,0,120,179,90,255)],False,
  'Отделите светлые малонасыщенные участки Луны от неба. Здесь важнее насыщенность S и яркость V, чем оттенок H.',
  ['У почти серого объекта насыщенность S мала, а яркость V заметно выше фона.', 'Разрешите весь диапазон H от 0 до 179, ограничьте S сверху, а V снизу. Границы включаются в маску.']),
 ('hsv-sky','HSV: маска голубого неба','sky.jpg',[(90,50,50,130,255,255)],False,
  'Выделите голубые и синие участки неба; белые облака с низкой насыщенностью не должны попасть в эту маску.',
  ['H отвечает за оттенок, S — за насыщенность, V — за яркость. Ограничение по одному H может захватить почти серые пиксели.', 'Используйте inRange с заданными границами всех трёх каналов. Сохраняйте именно маску, а не HSV-изображение.']),
 ('hsv-apples','HSV: зелёные участки яблок','apples.jpg',[(25,80,40,85,255,255)],False,
  'Получите маску зелёных и жёлто-зелёных участков яблок. Красные бока и тёмный фон останутся чёрными: цветовая маска не обязана выделять яблоко целиком.',
  ['Объект может содержать несколько цветов. Эта задача выделяет только участки заданного цвета, а не все яблоки целиком.', 'Нижняя граница V убирает тёмный фон; нижняя S убирает малонасыщенные участки. Соберите их вместе с диапазоном H.']),
 ('hsv-red','HSV: красный через два диапазона','img.jpg',[(0,120,60,15,255,255),(170,120,60,179,255,255)],False,
  'Выделите красно-оранжевые участки мяча. Красный находится по обе стороны границы шкалы H: одной маски недостаточно.',
  ['Постройте две маски через inRange: одну для начала шкалы оттенка, другую для её конца.', 'Объедините маски операцией cv2.bitwise_or. Не складывайте uint8-маски: при пересечении диапазонов возможно переполнение.']),
 ('hsv-color','HSV: яблоки на чёрном фоне','apples.jpg',[(25,80,40,85,255,255)],True,
  'Сохраните исходные BGR-цвета зелёных участков яблок, а остальные пиксели сделайте чёрными. В этой задаче результат — цветная фотография, а не чёрно-белая маска.',
  ['Сначала получите одноканальную маску зелёного тем же способом, что в предыдущей задаче про яблоки.', 'Передайте маску в cv2.bitwise_and(image, image, mask=mask). Применяйте её к исходному BGR-изображению, а не к HSV.']),
]
cat=json.loads((COURSE/'catalog.json').read_text())
cat=[t for t in cat if not t['slug'].startswith('hsv-')]
for slug,title,photo,ranges,color,intro,hints in LESSONS:
    bounds='; '.join(f'H={a}…{d}, S={b}…{e}, V={c}…{f}' for a,b,c,d,e,f in ranges)
    statement=(intro+' Прочитайте input.png и преобразуйте BGR в HSV (OpenCV: H от 0 до 179, S и V от 0 до 255). Диапазоны: '+bounds+'. Все границы включительны. '+
      ('Объедините два диапазона логическим ИЛИ. ' if len(ranges)>1 else '')+
      ('Сохраните цветной результат' if color else 'Сохраните одноканальную маску uint8: подходящий пиксель — 255, остальные — 0')+
      ' в output.png без изменения размеров. Проверка сравнивает пиксели на трёх версиях фотографии. На своём изображении можно экспериментировать отдельно.')
    prefix="import cv2\nimport numpy as np\n\nimage = cv2.imread('input.png')\n"
    code=prefix+"hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)\n"
    for i,(a,b,c,d,e,f) in enumerate(ranges): code+=f"mask{i} = cv2.inRange(hsv, ({a}, {b}, {c}), ({d}, {e}, {f}))\n"
    code+='mask = '+('cv2.bitwise_or(mask0, mask1)' if len(ranges)>1 else 'mask0')+'\n'
    code+=('result = cv2.bitwise_and(image, image, mask=mask)\n' if color else 'result = mask\n')+"cv2.imwrite('output.png', result)\n"
    image=cv2.imread(str(ROOT/'tutorial/static/hsv'/photo));h,w=image.shape[:2]
    image=cv2.resize(image,(640,round(h*640/w)),interpolation=cv2.INTER_AREA)
    variants=[image,cv2.flip(image,1),image[image.shape[0]//8:7*image.shape[0]//8,image.shape[1]//8:7*image.shape[1]//8].copy()]
    tests=[]
    for i,im in enumerate(variants):
        src=f'fixtures/hsv-{Path(photo).stem}-{i}.png';dst=f'expected/{slug}-{i}.png'
        cv2.imwrite(str(COURSE/src),im)
        hsv=cv2.cvtColor(im,cv2.COLOR_BGR2HSV);mask=np.zeros(im.shape[:2],dtype=np.uint8)
        for a,b,c,d,e,f in ranges: mask=cv2.bitwise_or(mask,cv2.inRange(hsv,(a,b,c),(d,e,f)))
        assert 0<np.count_nonzero(mask)<mask.size,(slug,i)
        result=cv2.bitwise_and(im,im,mask=mask) if color else mask
        cv2.imwrite(str(COURSE/dst),result)
        tests.append({'input':src,'expected':dst})
    cat.append(dict(slug=slug,title=title,statement=statement,starter=prefix+'\n# Выделите нужные пиксели и сохраните output.png\n',solution=code,tests=tests))
    article=dict(slug=slug,title=title,origin='authored',summary=intro,hints=hints,recommended=dict(title='Цветовая маска HSV',code=code,explanation='Преобразуем BGR в HSV, проверяем включительные границы каналов и сохраняем '+('исходные цвета под маской.' if color else 'маску 0/255.'),time_complexity='O(H × W)',space_complexity='O(H × W)'),alternatives=[],pitfalls=['Не путайте RGB с BGR: cv2.imread возвращает BGR.','У OpenCV оттенок H заканчивается на 179, не на 255.','Цветовая маска выделяет пиксели, а не распознаёт предметы.'],sources=[{'title':'Исходные учебные фотографии','url':'https://github.com/dimaystinov/dimaystinov.github.io'}])
    (ROOT/'knowledge/images'/f'{slug}.json').write_text(json.dumps(article,ensure_ascii=False,indent=2)+'\n')
(COURSE/'catalog.json').write_text(json.dumps(cat,ensure_ascii=False,indent=2)+'\n')
print('Generated 6 HSV tasks, 18 nonempty masks, four source photographs; OpenCV',cv2.__version__)
