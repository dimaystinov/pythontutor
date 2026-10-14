from tutorial.enrollment import teacher_students
import base64
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.http import FileResponse, Http404, JsonResponse, HttpResponseForbidden
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from evaldontevil import execute_python
from tutorial.image_course import catalog, canonical_image, material_path, image_matches, MAX_BYTES
from tutorial.models import ImageSubmission, ImageAssignment
from tutorial.forms import ImageAssignmentForm


def get_task(slug):
    for task in catalog():
        if task['slug'] == slug:
            return task
    raise Http404('Задание не найдено')


def image_index(request):
    tasks = catalog()
    if request.user.is_authenticated:
        for task in tasks:
            submissions = ImageSubmission.objects.filter(user=request.user, task_slug=task['slug'])
            task['status'] = 'ok' if submissions.filter(status='ok').exists() else ('error' if submissions.exists() else '')
    return render(request, 'image_index.html', {'tasks': tasks})


def image_task(request, slug):
    task = get_task(slug)
    tasks = catalog()
    index = next(i for i, item in enumerate(tasks) if item['slug'] == slug)
    following = tasks[index + 1] if index + 1 < len(tasks) else None
    next_task = {'url': reverse('image_task', args=[following['slug']]), 'title': following['title']} if following else None
    submission = ImageSubmission.objects.filter(user=request.user, task_slug=slug).first() if request.user.is_authenticated else None
    tests = [{'index': index, 'input_url': reverse('image_input', args=[slug, index])} for index in range(len(task['tests']))]
    from tutorial.knowledge import solved
    knowledge_unlocked = solved(request.user, image_slug=slug)
    from tutorial.task_help import task_hints
    hints = task_hints(slug, image=True)
    return render(request, 'image_task.html', {'task_hints': hints, 'next_task': next_task, 'task_list_url': reverse('image_index'), 'ai_kind':'image', 'ai_slug':slug, 'knowledge_unlocked': knowledge_unlocked, 'task': task, 'saved_code': submission.code if submission else task['starter'], 'tests': tests})


def image_input(request, slug, index):
    task = get_task(slug)
    if index < 0 or index >= len(task['tests']):
        raise Http404()
    return FileResponse(material_path(task['tests'][index]['input']).open('rb'), content_type='image/png')


def read_code(request):
    code = request.POST.get('code', '')
    if not code.strip() or len(code.encode('utf-8')) > 65536:
        raise ValueError('Введите программу размером не больше 64 КиБ.')
    return code


def execute_image(code, image):
    return execute_python(code, image=base64.b64encode(image).decode('ascii'))


@login_required
@require_POST
def image_run(request, slug):
    task = get_task(slug)
    try:
        code = read_code(request)
        upload = request.FILES.get('image')
        if upload and upload.size > MAX_BYTES:
            raise ValueError('Изображение должно быть не больше 2 МиБ.')
        data = upload.read(MAX_BYTES + 1) if upload else material_path(task['tests'][0]['input']).read_bytes()
        image = canonical_image(data)
    except ValueError as exc:
        return JsonResponse({'error': str(exc)}, status=400)
    result = execute_image(code, image)
    payload = {key: getattr(result, key, None) for key in ('result', 'stdout', 'stderr', 'image', 'exception')}
    # Keep the browser boundary safe even if the runner is misconfigured.
    if payload['image']:
        try:
            if len(payload['image']) > MAX_BYTES * 2:
                raise ValueError('Output image too large')
            payload['image'] = base64.b64encode(canonical_image(base64.b64decode(payload['image'], validate=True))).decode('ascii')
        except (ValueError, TypeError):
            payload.update(result='invalid_image', image=None, stderr='Сервис вернул некорректное изображение.')
    return JsonResponse(payload, status=503 if payload['result'] == 'internal_error' else 200)


@login_required
@require_POST
def image_submit(request, slug):
    task = get_task(slug)
    try:
        code = read_code(request)
    except ValueError as exc:
        return JsonResponse({'error': str(exc)}, status=400)
    tests = []
    for test in task['tests']:
        image = canonical_image(material_path(test['input']).read_bytes())
        result = execute_image(code, image)
        if result.result == 'internal_error':
            return JsonResponse({'status': 'unavailable', 'error': 'Сервис выполнения временно недоступен.'}, status=503)
        correct = result.result == 'ok' and image_matches(getattr(result, 'image', None), material_path(test['expected']).read_bytes())
        tests.append('ok' if correct else ('wrong_answer' if result.result == 'ok' else result.result))
        if result.result in ('realtime_limited', 'instructions_limited', 'output_limited', 'memory_limited'):
            tests.extend(['skipped'] * (len(task['tests']) - len(tests)))
            break
    status = 'ok' if tests and all(test == 'ok' for test in tests) else 'error'
    ImageSubmission.objects.create(user=request.user, task_slug=slug, code=code, status=status)
    return JsonResponse({'status': status, 'tests': tests, 'knowledge_url': reverse('knowledge_image', args=[slug]) if status == 'ok' else None})


@login_required
def image_assignments(request):
    is_teacher = request.user.is_staff
    if request.method == 'POST' and not is_teacher:
        return HttpResponseForbidden('Выдавать задания может преподаватель.')
    form = ImageAssignmentForm(request.POST if request.method == 'POST' else None, teacher=request.user) if is_teacher else None
    if form and request.method == 'POST' and form.is_valid():
        assignment = form.save(commit=False)
        assignment.created_by = request.user
        assignment.save()
        return redirect('image_assignments')
    queryset = ImageAssignment.objects.select_related('assignee', 'created_by')
    if is_teacher and not request.user.is_superuser:
        queryset = queryset.filter(created_by=request.user)
    elif not is_teacher:
        group = request.user.userprofile.study_group
        broadcast = Q(assignee__isnull=True, created_by=group.teacher) if group else Q(pk__in=[])
        queryset = queryset.filter(Q(assignee=request.user) | broadcast)
    assignments = []
    for assignment in queryset:
        users = User.objects.filter(pk=assignment.assignee_id) if assignment.assignee_id else teacher_students(assignment.created_by).filter(is_active=True)
        if not is_teacher:
            users = users.filter(pk=request.user.pk)
        progress = []
        for user in users:
            submissions = ImageSubmission.objects.filter(user=user, task_slug=assignment.task_slug)
            latest = submissions.first()
            progress.append({'user': user, 'status': 'ok' if submissions.filter(status='ok').exists() else (latest.status if latest else ''), 'time': latest.time if latest else None})
        assignments.append({'assignment': assignment, 'submissions': progress})
    return render(request, 'image_assignments.html', {'form': form, 'assignments': assignments, 'is_teacher': is_teacher})
