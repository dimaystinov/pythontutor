"""Scaffolds use only concepts from lesson one; never replace saved work."""
RULES = 'Ученик только начинает: используй input(), int(), print(), переменные и простую арифметику (+, -, *, /, //, %), склеивание строк. Не предлагай sum, map, списки, циклы, генераторы, f-строки, divmod и импорт библиотек. Для суммы трёх чисел показывай сложение через print(a + b + c).'
STARTERS = {
 'aplusbplusc': ('a = int(input())\nb = int(input())\nc = int(input())\n# В скобках print напишите сумму a, b и c.\nprint()\n', 'print(1 + 2 + 3)', 'Знак + складывает числа, а print выводит результат. Замените числа переменными из входных данных.'),
 'rect_triangle_square': ('a = int(input())\nb = int(input())\n# В скобках print напишите выражение для площади.\nprint()\n', 'print(6 / 2)', 'Оператор / делит числа. Вспомните формулу площади прямоугольного треугольника.'),
 'apples': ('n = int(input())\nk = int(input())\n# Выведите число яблок каждому, затем остаток в корзине.\nprint()\nprint()\n', 'print(7 // 2)\nprint(7 % 2)', '// даёт целую часть частного, % — остаток. Здесь n — школьники, k — яблоки.'),
 'electronic_watch': ('n = int(input())\n# Найдите часы и минуты. Выведите их через print.\nprint()\n', 'print(75 // 60)\nprint(75 % 60)', 'В часе 60 минут, в сутках 24 часа. Часы на циферблате начинаются заново после суток.'),
 'hello_harry': ('name = input()\n# Соберите приветствие из текста и переменной name.\nprint()\n', "print('Привет, ' + 'Аня' + '!')", 'Знак + соединяет строки. Не забудьте нужный пробел и знаки препинания из условия.'),
}
def guide(slug):
    if slug not in STARTERS:
        return None
    code, example, hint = STARTERS[slug]
    return {'code': code, 'example': example, 'hint': hint}
