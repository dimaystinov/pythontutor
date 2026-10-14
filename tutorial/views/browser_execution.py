"""Deliver client tests and save explicitly unverified browser results. Never execute code."""
import base64
import json
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse, Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST
from tutorial.models import Problem, Submission, ImageSubmission, UserProfile
from tutorial.problems import load_problem
from tutorial.image_course import catalog, material_path


def task_data(kind, slug):
    if kind == 'problem':
        problem = get_object_or_404(Problem, urlname=slug)
        return problem, load_problem(problem)
    task = next((t for t in catalog() if t['slug'] == slug), None)
    if kind != 'image' or task is None:
        raise Http404
    return None, task


@require_GET
def runtime_worker(request):
    from pathlib import Path
    origin = request.build_absolute_uri('/').rstrip('/')
    static = origin + settings.STATIC_URL
    source = (Path(settings.BASE_DIR) / 'tutorial/static/browser/worker.mjs').read_text()
    source = source.replace('../vendor/pyodide/', static+'vendor/pyodide/')
    source = source.replace("new URL('engine.zip',import.meta.url)", json.dumps(static+'browser/engine.zip'))
    response = HttpResponse(source, content_type='text/javascript')
    response['Content-Security-Policy'] = ("default-src 'none'; script-src 'wasm-unsafe-eval' " + static + "vendor/pyodide/; connect-src " + static + "browser/ " + static + "vendor/pyodide/")
    response['Cache-Control'] = 'no-store'
    return response


@require_GET
def tests(request, kind, slug):
    if settings.EXECUTION_MODE != 'browser':
        raise Http404
    _, task = task_data(kind, slug)
    if kind == 'problem':
        items = [{'stdin': x, 'answer': y} for x,y in zip(task['tests'],task['answers'])]
    else:
        items = [{'image': base64.b64encode(material_path(t['input']).read_bytes()).decode(),
                  'expected': base64.b64encode(material_path(t['expected']).read_bytes()).decode()} for t in task['tests']]
    response = JsonResponse({'tests': items})
    response['Cache-Control'] = 'no-store'
    return response


@login_required
@require_POST
def submit(request, kind, slug):
    if settings.EXECUTION_MODE != 'browser':
        return JsonResponse({'error':'Клиентская проверка отключена.'}, status=409)
    problem, task = task_data(kind, slug)
    try:
        payload=json.loads(request.body)
        code=payload['code']; results=payload['results']
        if not isinstance(code,str) or not code.strip() or len(code.encode())>65536:
            raise ValueError
        if not isinstance(results,list) or len(results)!=len(task['tests']):
            raise ValueError
        verdicts=[]
        allowed={'ok','wrong_answer','unhandled_exception','stderr','realtime_limited','instructions_limited','output_limited','invalid_image','skipped'}
        for index,result in enumerate(results):
            if not isinstance(result,dict) or result.get('result') not in allowed:
                raise ValueError
            verdict=result['result']
            verdicts.append(verdict)
    except (ValueError, TypeError, KeyError):
        return JsonResponse({'error':'Некорректный отчёт проверки.'}, status=400)
    status='ok' if verdicts and all(v=='ok' for v in verdicts) else 'error'
    if kind=='problem':
        profile,_=UserProfile.objects.get_or_create(user=request.user)
        saved_status='accepted' if status=='ok' and profile.course and profile.course.ok_ac_policy==1 else status
        Submission.objects.create(user=request.user,problem=problem,code=code,status=dict((v,k) for k,v in Submission.STATUS_CHOICES)[saved_status],execution_source='browser')
    else:
        ImageSubmission.objects.create(user=request.user,task_slug=slug,code=code,status=status,execution_source='browser')
    return JsonResponse({'status':status,'tests':verdicts,'execution_source':'browser',
        'knowledge_url':reverse('knowledge_problem' if kind=='problem' else 'knowledge_image',args=[slug]) if status=='ok' else None})
