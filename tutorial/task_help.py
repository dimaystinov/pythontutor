"""Optional hints and explanatory figures; no reference programs in hints."""
from tutorial.knowledge import article
from tutorial.beginner import guide

FIGURES = {
 'rect_triangle_square': ('triangle', 'Катеты a и b образуют прямой угол. Рисунок условный, не в масштабе.'),
 'hypot': ('triangle', 'a и b — катеты; c — гипотенуза напротив прямого угла.'),
 'apples': ('apples', 'Яблоки делят поровну между школьниками; часть может остаться в корзине.'),
 'desks': ('desks', 'За одной партой два места. Парты нужны отдельно для каждого класса.'),
 'electronic_watch': ('digital-clock', 'Часы и минуты — два отдельных числа. После 23 часов начинаются новые сутки.'),
 'mkad': ('ring-road', 'Кольцевая дорога длиной 109 км; отсчёт начинается у отметки 0.'),
 'chocolate': ('chocolate', 'Шоколадка состоит из n рядов и m столбцов. Разлом — одна прямая линия.'),
 **{s: ('clock', 'Угол часовой стрелки отсчитывается от положения «12 часов» по часовой стрелке.') for s in ['watch_1','watch_2','watch_3']},
 **{s: ('chess-coordinates', 'Клетку задают два числа: номер столбца и номер строки, от 1 до 8.') for s in ['chess_board','bishop_move','rook_move','queen_move','king_move','knight_move','lists_queens']},
}

def task_hints(slug, image=False):
    data = article(slug, image=image) or {}
    if len(data.get('hints', [])) == 2:
        return [{'text': text, 'example': ''} for text in data['hints']]
    beginner = None if image else guide(slug)
    first = beginner['hint'] if beginner else data.get('summary', 'Разберите входные данные и определите, что должно получиться на выходе.')
    pitfalls = data.get('pitfalls', [])
    second = pitfalls[0] if pitfalls else data.get('recommended', {}).get('explanation', 'Проверьте решение на маленьком примере и на граничных значениях.')
    if slug == 'rect_triangle_square' and not image:
        second = r'Площадь прямоугольного треугольника: \( S = \frac{a \times b}{2} \), где a и b — длины катетов. В Python произведение записывают через *, а обычное деление — через /: a * b / 2.'
    return [{'text': first, 'example': beginner['example'] if beginner else ''}, {'text': second, 'example': ''}]

def task_figure(slug):
    if slug not in FIGURES:
        return None
    name, caption = FIGURES[slug]
    return {'src': 'images/tasks/' + name + '.svg', 'caption': caption}
