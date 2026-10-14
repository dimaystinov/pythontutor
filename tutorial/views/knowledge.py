from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.http import Http404
from django.urls import reverse
from django.views.decorators.cache import never_cache
from tutorial.models import Problem, Submission, ImageSubmission
from tutorial.knowledge import article, solved
from tutorial.image_course import catalog


@login_required
@never_cache
def knowledge_index(request):
    passed = set(Submission.objects.filter(user=request.user, status__in=[1, 2]).values_list('problem_id', flat=True))
    images_passed = set(ImageSubmission.objects.filter(user=request.user, status='ok').values_list('task_slug', flat=True))
    entries = []
    for problem in Problem.objects.order_by('probleminlesson__lesson__lessonincourse__order', 'probleminlesson__order'):
        data = article(problem.urlname)
        if data:
            entries.append({'title': data['title'], 'unlocked': problem.pk in passed, 'url': reverse('knowledge_problem', args=[problem.urlname])})
    for task in catalog():
        if article(task['slug'], image=True):
            entries.append({'title': 'OpenCV: ' + task['title'], 'unlocked': task['slug'] in images_passed, 'url': reverse('knowledge_image', args=[task['slug']])})
    return render(request, 'knowledge_index.html', {'entries': entries, 'unlocked_count': sum(e['unlocked'] for e in entries)})


@login_required
@never_cache
def knowledge_problem(request, slug):
    problem = get_object_or_404(Problem, urlname=slug)
    relation = problem.probleminlesson_set.select_related('lesson').first()
    task_url = reverse('problem_in_lesson', args=[relation.lesson.urlname, slug]) if relation else reverse('home')
    if not solved(request.user, problem=problem):
        return render(request, 'knowledge_locked.html', {'task_url': task_url}, status=403)
    data = article(slug)
    if data is None:
        raise Http404('Разбор ещё не опубликован')
    own = Submission.objects.filter(user=request.user, problem=problem, status__in=[1, 2]).latest('time')
    return render(request, 'knowledge_article.html', {'article': data, 'task_url': task_url, 'own_code': own.code})


@login_required
@never_cache
def knowledge_image(request, slug):
    task = next((t for t in catalog() if t['slug'] == slug), None)
    if task is None:
        raise Http404
    task_url = reverse('image_task', args=[slug])
    if not solved(request.user, image_slug=slug):
        return render(request, 'knowledge_locked.html', {'task_url': task_url}, status=403)
    data = article(slug, image=True)
    if data is None:
        raise Http404
    own = ImageSubmission.objects.filter(user=request.user, task_slug=slug, status='ok').latest('time')
    return render(request, 'knowledge_article.html', {'article': data, 'task_url': task_url, 'own_code': own.code})
