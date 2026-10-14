from json import dumps

from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST

from tutorial.models import Lesson

from errors import translate_error
from evaldontevil import execute_python


def visualizer(request):
    if 'lesson' in request.GET:
        lesson = get_object_or_404(Lesson, urlname=request.GET['lesson'])
        if lesson is not None:
            navigation = {'lesson': lesson}

    code = request.POST.get('code', '')
    input_data = request.POST.get('input', '')

    return render(request, 'visualizer.html', locals())


def explain_error(exc, code):
    msg = exc.get('exception_type', '') + ': ' + exc.get('exception_msg', '')
    lines = code.split('\n')
    line_number = exc.get('line') or 1
    line = lines[line_number - 1] if 0 < line_number <= len(lines) else ''
    try:
        translation = translate_error(msg, line)
    except:
        translation = ''
    exc['exception_translation'] = translation


@require_POST
def execute(request):
    # AJAX request
    # method: POST
    # params: user_script, input_data
    post = request.POST
    if 'user_script' in post and 'input_data' in post:
        user_script = post['user_script']
        input_data = post['input_data']
        if len(user_script.encode('utf-8')) > 65536 or len(input_data.encode('utf-8')) > 65536:
            return HttpResponseBadRequest('Программа или ввод слишком длинные')
        explain = False if post.get('explain', True) == 'false' else True

        res = execute_python(user_script, stdin=input_data, explain=explain).__dict__

        if explain:
            res.pop('stdout', None) # exact the same information is present on the last frame - why should it be duplicated?
            res.pop('stderr', None) # see ^

        if res.get('trace'):
            event = res['trace'][-1]
            if event['event'] == 'exception' or event['event'] == 'uncaught_exception':
                explain_error(event, user_script)

        if 'exception' in res and res['exception'] is not None:
            explain_error(res['exception'], user_script)

        return HttpResponse(dumps(res), content_type='application/json')

    else:
        return HttpResponseBadRequest()
