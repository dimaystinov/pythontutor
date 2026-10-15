"""Public, account-free offline course snapshots. Never cache authenticated HTML."""
from pathlib import Path
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import render
from django.test import RequestFactory
from django.urls import resolve, reverse
from django.views.decorators.http import require_GET
from tutorial.models import LessonInCourse, ProblemInLesson
from tutorial.image_course import catalog
from tutorial.views import DEFAULT_COURSE

PUBLIC_VIEWS = {'home', 'old', 'lesson_in_course', 'problem_in_lesson', 'image_index', 'image_task', 'visualizer', 'pwa'}
VERSION = 'pwa-20261015-desktop2'

@require_GET
def dashboard(request):
    from tutorial.problems import load_problem
    tasks = {}
    for entry in ProblemInLesson.objects.filter(lesson__lessonincourse__course__urlname=DEFAULT_COURSE).select_related('lesson', 'problem'):
        tasks['problem:' + entry.problem.urlname] = {
            'title': load_problem(entry.problem)['name'],
            'lesson': entry.lesson.urlname,
            'url': reverse('problem_in_lesson', args=[entry.lesson.urlname, entry.problem.urlname]),
        }
    for task in catalog():
        tasks['image:' + task['slug']] = {
            'title': task['title'], 'url': reverse('image_task', args=[task['slug']]), 'lesson': 'opencv',
        }
    lessons = [
        {'id': entry.lesson.urlname, 'title': f'Занятие {index}. {entry.lesson.title}',
         'url': reverse('lesson_in_course', args=[entry.lesson.urlname]) + '#problems'}
        for index, entry in enumerate(LessonInCourse.objects.filter(course__urlname=DEFAULT_COURSE).select_related('lesson'), 1)
    ]
    lessons.append({'id': 'opencv', 'title': 'OpenCV — обработка изображений', 'url': reverse('image_index')})
    return render(request, 'pwa.html', {'progress_tasks': tasks, 'progress_lessons': lessons})

@require_GET
def service_worker(request):
    response = HttpResponse((Path(settings.BASE_DIR)/'tutorial/static/pwa/sw.js').read_text(), content_type='text/javascript')
    response['Cache-Control'] = 'no-cache'
    response['Service-Worker-Allowed'] = '/'
    return response

@require_GET
def manifest(request):
    return JsonResponse({'id':'/','name':'Питонтьютор — Python офлайн','short_name':'Питонтьютор','lang':'ru',
      'start_url':'/pwa/','scope':'/','display':'standalone','background_color':'#ffffff','theme_color':'#e3ebf1',
      'icons':[{'src':f'/static/pwa/icon-{size}.png','sizes':f'{size}x{size}','type':'image/png','purpose':'any maskable'} for size in (192,512)]}, content_type='application/manifest+json')

@require_GET
def download_manifest(request):
    if settings.EXECUTION_MODE != 'browser': raise Http404
    pages=['/','/visualizer/','/images/','/pwa/']
    pages.append('/knowledge/')
    resources=['/browser/worker/','/manifest.webmanifest']
    for entry in LessonInCourse.objects.filter(course__urlname=DEFAULT_COURSE).select_related('lesson'):
        pages.append(reverse('lesson_in_course',args=[entry.lesson.urlname]))
    for entry in ProblemInLesson.objects.filter(lesson__lessonincourse__course__urlname=DEFAULT_COURSE).select_related('lesson','problem'):
        pages.append(reverse('problem_in_lesson',args=[entry.lesson.urlname,entry.problem.urlname]))
        pages.append(reverse('knowledge_problem',args=[entry.problem.urlname]))
        resources.append('/browser/tests/problem/'+entry.problem.urlname+'/')
    for task in catalog():
        pages.append(reverse('image_task',args=[task['slug']]))
        pages.append(reverse('knowledge_image',args=[task['slug']]))
        resources.append('/browser/tests/image/'+task['slug']+'/')
        resources.extend(reverse('image_input',args=[task['slug'],i]) for i in range(len(task['tests'])))
    root=Path(settings.BASE_DIR)/'tutorial/static'
    for file in sorted(root.rglob('*')):
        if file.is_file() and file.suffix in {'.html','.js','.mjs','.css','.png','.jpg','.jpeg','.gif','.svg','.ttf','.woff','.woff2','.eot','.wasm','.zip','.whl','.json'} and 'tests' not in file.relative_to(root).parts:
            resources.append(settings.STATIC_URL+file.relative_to(root).as_posix())
    return JsonResponse({'version':VERSION,'pages':list(dict.fromkeys(pages)),'resources':list(dict.fromkeys(resources))})

@require_GET
def public_page(request):
    if settings.EXECUTION_MODE != 'browser': raise Http404
    target=request.GET.get('path','/')
    if not target.startswith('/') or '?' in target or '#' in target: raise Http404
    match=resolve(target)
    if match.url_name not in PUBLIC_VIEWS|{'knowledge_index','knowledge_problem','knowledge_image'}: raise Http404
    local=RequestFactory().get(target, HTTP_HOST=request.get_host(), secure=request.is_secure())
    local.user=AnonymousUser(); local.session={}; local.pwa_offline=True
    if match.url_name in {'knowledge_problem','knowledge_image'}:
        from tutorial.knowledge import article
        slug=match.kwargs['slug'];kind='image' if match.url_name=='knowledge_image' else 'problem'
        data=article(slug,image=kind=='image')
        if data is None: raise Http404
        if kind=='image': task_url=reverse('image_task',args=[slug])
        else:
            entry=ProblemInLesson.objects.filter(problem__urlname=slug).select_related('lesson').first()
            task_url=reverse('problem_in_lesson',args=[entry.lesson.urlname,slug])
        return render(local,'knowledge_article.html',{'article':data,'task_url':task_url,'own_code':'','local_kind':kind,'local_slug':slug})
    if match.url_name=='knowledge_index':
        from tutorial.knowledge import article
        entries=[]
        for entry in ProblemInLesson.objects.filter(lesson__lessonincourse__course__urlname=DEFAULT_COURSE).select_related('problem'):
            data=article(entry.problem.urlname)
            if data: entries.append({'title':data['title'],'url':reverse('knowledge_problem',args=[entry.problem.urlname]),'unlocked':False})
        for task in catalog(): entries.append({'title':task['title'],'url':reverse('knowledge_image',args=[task['slug']]),'unlocked':False})
        return render(local,'knowledge_index.html',{'entries':entries,'unlocked_count':0})
    view=getattr(match.func,'__wrapped__',match.func)
    response=view(local,*match.args,**match.kwargs)
    response['Cache-Control']='public, max-age=0'
    return response
