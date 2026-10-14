# evaldontevil
#  (eval, don't evil)
#  part of the Pythontutor project
#  https://github.com/vpavlenko/pythontutor-ru


# This is a modified copy of pg_logger.py from the
#   Online Python Tutor (https://github.com/pgbovine/OnlinePythonTutor/)
# It is Python 3 ready.

# -----------------------------------------------------------------------------

# Online Python Tutor
# https://github.com/pgbovine/OnlinePythonTutor/
# 
# Copyright (C) 2010-2012 Philip J. Guo (philip@pgbovine.net)
# 
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
# 
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# -----------------------------------------------------------------------------

import math
import types

real_to_small_IDs = {}

def encode(value):
    budget = [300]
    def visit(obj, seen, depth=0):
        budget[0] -= 1
        if budget[0] < 0 or depth > 12:
            return '<truncated>'
        typ = type(obj)
        if obj is None or typ in (bool, int):
            return obj
        if typ is float:
            return obj if math.isfinite(obj) else str(obj)
        if typ is str:
            return obj[:4096]
        identity = id(obj)
        ident = real_to_small_IDs.setdefault(identity, len(real_to_small_IDs) + 1)
        if identity in seen:
            return ['CIRCULAR_REF', ident]
        seen = seen | {identity}
        if typ in (list, tuple, set, frozenset):
            return [('SET' if typ is frozenset else typ.__name__.upper()), ident] + [visit(item, seen, depth + 1) for item in list(obj)[:100]]
        if typ is dict:
            return ['DICT', ident] + [[visit(k, seen, depth+1), visit(v, seen, depth+1)] for k, v in list(obj.items())[:100]]
        if isinstance(obj, (types.FunctionType, types.MethodType, types.ModuleType)):
            return [typ.__name__, ident, getattr(obj, '__name__', typ.__name__)]
        if isinstance(obj, type):
            return ['CLASS', obj.__name__, ident, [base.__name__ for base in obj.__bases__]]
        # Avoid evaluating descriptors/properties or arbitrary repr implementations.
        try:
            attrs = object.__getattribute__(obj, '__dict__')
        except (AttributeError, TypeError):
            attrs = {}
        return ['INSTANCE', typ.__name__, ident] + [[k, visit(v, seen, depth+1)] for k,v in list(attrs.items())[:100] if not k.startswith('__')]
    return visit(value, set())
