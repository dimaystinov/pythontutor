# coding=utf-8

'''
translate_error() checks error translations upside down, the first match is being displayed.
Every error has either only |regexp|, in which case the |error_msg| received from interpreter should
match this |regexp|, or |regexp| and |detector|, in which case |regexp| should match |error_msg| and
|detector| should return True.

The groups in |regexp| should go in an increasing order: {0}, {1}, {2}, ...

For testing purposes every error translation should have example of code which causes this type of
error.
'''

import re


class ErrorTranslation:
    def __init__(self, regexp, translation, detector=None, code=None):
        self.source_regexp = regexp
        self.regexp = re.sub(r'\\{\d+\\}', '(.+)', re.escape(regexp))
        self.translation = translation
        self.detector = detector
        self.code = code

    def is_matched(self, error_msg, code_line):
        if self.detector:
            return re.match(self.regexp, error_msg) and self.detector(error_msg, code_line)
        return re.match(self.regexp, error_msg)

    def get_translation(self, error_msg):
        return self.translation.format(*re.match(self.regexp, error_msg).groups())

    def __str__(self):
        return 'Error({0}, {1})'.format(self.regexp, self.translation)


def detect_missing_trailing_colon(error_msg, code_line):
    tokens = code_line.split()
    return (tokens and tokens[0] in ['for', 'while', 'if', 'else', 'elif'] and
            code_line.rstrip()[-1] != ':')


def detect_assignment_instead_of_equals(error_msg, code_line):
    tokens = code_line.split()
    return tokens and tokens[0] in ['while', 'if', 'elif'] and re.search(r'[^=]=[^=]', code_line)


def detect_alone_elif(error_msg, code_line):
    tokens = code_line.split()
    return tokens and tokens[0].startswith('elif') and (':' in tokens[0] or len(tokens) <= 2)


ERROR_TRANSLATIONS = [ErrorTranslation(**entry) for entry in [
    {
    'regexp':
        'IndexError: list index out of range',

    'translation':
        'Ошибка обращения по индексу: выход за границы списка',

    'code':
        '[][0]',
    },

    {
    'regexp':
        """IndexError: string index out of range""",

    'translation':
        """Ошибка обращения по индексу: выход за границы строки""",

    'code':
        '""[0]',
    },

    {
    'regexp':
        """EOFError: EOF when reading a line""",

    'translation':
        """Ошибка ввода-вывода: попытка считать из входных данных,
    которые уже закончились.""",

    'code':
        'input()',
    },

    {
    'regexp':
        """TypeError: not all arguments converted during string formatting""",

    'translation':
        """Не все аргументы попали в строку форматирования.
    Возможно, вы делите строку на число с остатком
    (а надо делить число на число).""",

    'code':
        '"1" % 2',
    },

    {
    'regexp':
        """IndentationError: expected an indented block""",

    'translation':
        """Ошибка: ожидается блок кода с отступом""",

    'code':
        'if True:\n'
        'print(42)',
    },

    {
    'regexp':
        """IndentationError: unexpected indent""",

    'translation':
        """Ошибка: внезапно возник блок кода с отступом""",

    'code':
        '    print(42)',
    },

    {
    'regexp':
        """NameError: name '{0}' is not defined""",

    'translation':
        """Ошибка поиска имени: имя '{0}' не связано ни с каким объектом""",

    'code':
        'print(a)',
    },

    {
    'regexp':
        """TypeError: unsupported operand type(s) for +: 'int' and 'str'""",

    'translation':
        """Ошибка типов: нельзя прибавить число к строке
    Попробуйте сначала преобразовать его к строке так: str(42)""",

    'code':
        '42 + "a"',
    },

    {
    'regexp':
        """TypeError: Can't convert '{0}' object to str implicitly""",

    'translation':
        """Ошибка типов: нельзя прибавить к строке объект типа '{0}'
    Попробуйте сначала преобразовать его к строке через str(...)""",

    'code':
        '"a" + 42',
    },

    {
    'regexp':
        """TypeError: unsupported operand type(s) for {0}: '{1}' and '{2}'""",

    'translation':
        """Ошибка типов: невозможно выполнить операцию '{0}'
    с объектами типов '{1}' и '{2}'""",

    'code':
        '"a" - "b"',
    },

    {
    'regexp':
        """TypeError: '{0}' object cannot be interpreted as an integer""",

    'translation':
        """Ошибка типов: требуется передать число, а передан объект типа {0}.
    Так бывает, если по ошибке написать <code>range(my_list)</code>
    вместо <code>range(len(my_list))</code>""",

    'code':
        'range([])',
    },

    {
    'regexp':
        """TypeError: 'str' object does not support item assignment""",

    'translation':
        """Строки в Python неизменяемы.
    Нельзя присвоить что-нибудь отдельному символу строки.
    Чтобы изменить символ, используйте срезы:
    <code>text = text[:4] + '$' + text[5:]</code>""",

    'code':
        's = "a"\n'
        's[0] = "b"',
    },

    {
    'regexp':
        """TypeError: '{0}' object does not support item assignment""",

    'translation':
        """Нельзя присвоить что-нибудь элементу в объекте типа '{0}'""",

    'code':
        'a = (1,)\n'
        'a[0] = 2',
    },

    {
    'regexp':
        """SyntaxError: EOL while scanning string literal""",

    'translation':
        """Перевод строки обнаружен раньше, чем закончилась строковая константа
    Наверно, вы забыли закрыть кавычку""",

    'code':
        's = "a\n'
        'b"',
    },

    {
    'regexp':
        """SyntaxError: invalid syntax""",

    'detector':
        lambda error_msg, code_line: ':=' in code_line,

    'translation':
        """Ошибка: неправильный синтаксис
    В Питоне ":=" не является оператором присваивания
    Неверно: variable := 42
    Правильно: variable = 42""",

    'code':
        'a := 42',
    },

    {
    'regexp':
        """SyntaxError: invalid syntax""",

    'detector': detect_missing_trailing_colon,

    'translation':
        """Ошибка: неправильный синтаксис
    В конце строки пропущено двоеточие""",

    'code':
        'if True\n'
        '    pass',
    },

    {
    'regexp':
        """SyntaxError: invalid syntax""",

    'detector': detect_assignment_instead_of_equals,

    'translation':
        """Ошибка: неправильный синтаксис
    Похоже, надо заменить '=' на '=='""",

    'code':
        'if a = 42:\n'
        '    pass',
    },

    {
    'regexp':
        """SyntaxError: invalid syntax""",

    'detector': detect_alone_elif,

    'translation':
        """Ошибка: неправильный синтаксис
    elif используется только вместе с каким-нибудь условием.
    Замените на "elif условие:" или на "else:\"""",

    'code':
        'if True:\n'
        '    pass\n'
        'elif:\n'
        '    pass',
    },

    {
    'regexp':
        """ZeroDivisionError: division by zero""",

    'translation':
        """Деление на ноль""",

    'code':
        '1 / 0',
    },

    {
    'regexp':
        """ZeroDivisionError: float division by zero""",

    'translation':
        """Деление на ноль""",

    'code':
        '1.0 / 0',
    },

    {
    'regexp':
        """TypeError: '{0}' object is not iterable""",

    'translation':
        """Возможно, вы использовали for i in 5
    вместо for i in range(5)""",

    'code':
        'for i in 5:\n'
        '    pass',
    },

    {
    'regexp':
        """TypeError: string indices must be integers""",

    'translation':
        """Индексы строки должны быть числами.
    Возможно, вы написали s[2,5] вместо s[2:5].
    В срезах аргументы разделяются двоеточиями.""",

    'code':
        '""[2,5]',
    },

    {
    'regexp':
        """TypeError: slice indices must be integers or None or have an __index__ method""",

    'translation':
        """Параметры среза должны быть числами""",

    'code':
        '""["a":"b"]',
    },

    {
    'regexp':
        """TypeError: can't multiply sequence by non-int of type '{0}'""",

    'translation':
        """Невозможно умножить последовательность на что-то, не являющееся целым числом,
    а имеющее тип '{0}'.""",

    'code':
        '[] * "a"',
    },

    {
    'regexp':
        """TypeError: '{0}' object is not subscriptable""",

    'translation':
        """Недопустимо брать индекс у объекта типа '{0}'.
    Возможно, вы написали квадратные скобки вместо круглых.""",

    'code':
        'str[42]',
    },

    {
    'regexp':
        """TypeError: list indices must be integers, not {0}""",

    'translation':
        """Индексы в списке должны быть целыми числами, а не объектами типа {0}""",

    'code':
        '[]["a"]',
    },

    {
    'regexp':
        """TypeError: sequence item 0: expected str instance, int found""",

    'translation':
        """В параметр join передан список не из строк, а из объектов типа '{0}'.
    Как обойти проблему: ' '.join([str(i) for i in my_list]""",

    'code':
        '"".join([1])'
    },

    {
    'regexp':
        """UnboundLocalError: local variable {0} referenced before assignment""",

    'translation':
        """Попытка взять значение локальной переменной {0},
    которая не была проинициализирована""",

    'code':
        'def f():\n'
        '    print(a)\n'
        '    a = 42\n'
        'f()',
    },

    {
    'regexp':
        """ValueError: invalid literal for int() with base 10: {0}""",

    'translation':
        """Нельзя перевести строку {0} в целое число""",

    'code':
        'int("a")',
    },

    {
    'regexp':
        """IndentationError: unindent does not match any outer indentation level""",

    'translation':
        """В вашей программе всё очень плохо с отступами.""",

    'code':
        'if True:\n'
        '    pass\n'
        '  else:\n'
        '      pass',
    },

    {
    'regexp':
        """ValueError: need more than {0} values to unpack""",

    'translation':
        """Неправильное множественное присваивание:
    справа стоит {0} объекта, а слева переменных больше.""",

    'code':
        'x, y, z = 1, 2',
    },

    {
    'regexp':
        """ValueError: too many values to unpack""",

    'translation':
        """Неправильное множественное присваивание:
    справа стоит больше объектов, чем слева переменных.""",

    'code':
        'x, y = 1, 2, 3',
    },
]]


def translate_error(error_msg, code_line):
    for error in ERROR_TRANSLATIONS:
        if error.is_matched(error_msg, code_line):
            explanation = error.get_translation(error_msg)
            return explanation
    return None
