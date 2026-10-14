# evaldontevil
#  (eval, don't evil)
#  part of the Pythontutor project
#  https://github.com/vpavlenko/pythontutor-ru


# This is a modified copy of pg_logger.py from the
#   Online Python Tutor (https://github.com/pgbovine/OnlinePythonTutor/)
# It is Python 3 ready, and less restrictive.

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

import builtins
import io
import json
import sys
import traceback
from .execplainator_encoder import encode, real_to_small_IDs

MAX_EXECUTED_LINES = 1000
MAX_OUTPUT = 65536
MAX_TRACE_BYTES = 2 * 1024 * 1024

class LimitReached(BaseException):
    pass

class BoundedOutput(io.StringIO):
    def write(self, value):
        if self.tell() + len(value) > MAX_OUTPUT:
            super().write(value[:max(0, MAX_OUTPUT-self.tell())])
            raise LimitReached('output_limited')
        return super().write(value)

def parse_exception(error):
    line = getattr(error, 'lineno', None) or 1
    for frame in traceback.extract_tb(error.__traceback__):
        if frame.filename == '<string>':
            line = frame.lineno
    message = str(error)[:4096]
    return {'line': line, 'offset': getattr(error, 'offset', None),
            'exception_type': type(error).__name__, 'exception_msg': message,
            'exception_str': type(error).__name__ + ': ' + message}


def _execute(code, input_data, explain):
    real_to_small_IDs.clear()
    stdout, stderr = BoundedOutput(), BoundedOutput()
    previous = sys.stdin, sys.stdout, sys.stderr
    namespace = {'__name__': '__main__', '__builtins__': builtins.__dict__}
    entries, trace_bytes = [], [0]
    result = {'result': 'ok', 'stdout': '', 'stderr': '', 'exception': None}
    def variables(mapping):
        return {k: encode(v) for k,v in list(mapping.items())[:100] if not k.startswith('__')}
    def snapshot(frame, event, arg):
        if frame.f_code.co_filename != '<string>':
            return snapshot
        if event not in ('call', 'line', 'return', 'exception'):
            return snapshot
        if len(entries) >= MAX_EXECUTED_LINES:
            raise LimitReached('instructions_limited')
        stack, current = [], frame
        while current and current.f_code.co_filename == '<string>' and current.f_code.co_name != '<module>':
            local = variables(current.f_locals)
            if current is frame and event == 'return':
                local['__return__'] = encode(arg)
            stack.append([current.f_code.co_name, local])
            current = current.f_back
        entry = {'event': 'step_line' if event == 'line' else event,
                 'line': max(1, frame.f_lineno), 'func_name': frame.f_code.co_name,
                 'globals': variables(namespace), 'stack_locals': stack,
                 'stdout': stdout.getvalue(), 'stderr': stderr.getvalue()}
        if event == 'exception':
            entry.update(parse_exception(arg[1]))
        trace_bytes[0] += len(json.dumps(entry, ensure_ascii=True))
        if trace_bytes[0] > MAX_TRACE_BYTES:
            raise LimitReached('instructions_limited')
        entries.append(entry)
        return snapshot
    try:
        sys.stdin, sys.stdout, sys.stderr = io.StringIO(input_data), stdout, stderr
        compiled = compile(code, '<string>', 'exec')
        if explain:
            sys.settrace(snapshot)
        builtins.exec(compiled, namespace, namespace)
    except LimitReached as error:
        result['result'] = str(error)
    except BaseException as error:
        result['result'] = 'unhandled_exception'
        result['exception'] = parse_exception(error)
        if explain:
            entries.append({'event': 'uncaught_exception', 'func_name': '<module>',
                            'globals': {}, 'stack_locals': [], 'stdout': stdout.getvalue(),
                            'stderr': stderr.getvalue(), **result['exception']})
    finally:
        sys.settrace(None)
        sys.stdin, sys.stdout, sys.stderr = previous
    result.update(stdout=stdout.getvalue(), stderr=stderr.getvalue())
    if result['result'] == 'ok' and result['stderr']:
        result['result'] = 'stderr'
    if explain:
        if result['result'] == 'instructions_limited':
            entries.append({'event': 'instruction_limit_reached', 'exception_msg': 'Trace limit reached'})
        if not entries:
            entries.append({'event': 'return', 'line': 1, 'func_name': '<module>', 'globals': {},
                            'stack_locals': [], 'stdout': result['stdout'], 'stderr': result['stderr']})
        result['trace'] = entries
    return result


def exec(code, input_data=''):
    return _execute(code, input_data, True)


def simple_exec(code, input_data=''):
    return _execute(code, input_data, False)
