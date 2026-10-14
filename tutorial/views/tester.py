from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from tutorial.models import Problem, Submission, UserProfile
from tutorial.problems import load_problem
from tutorial.tester import run_test

@login_required
@require_POST
def tester_submit(request):
    code = request.POST.get('user_code')
    name = request.POST.get('problem')
    if code is None or not name or len(code.encode('utf-8')) > 65536:
        return JsonResponse({'error': 'Некорректный запрос или слишком длинная программа'}, status=400)
    problem_db = get_object_or_404(Problem, urlname=name)
    problem = load_problem(problem_db)
    result = {'status': 'ok', 'tests': []}
    for test_id, (test_input, test_answer) in enumerate(zip(problem['tests'], problem['answers'])):
        test_status = run_test(code, test_input, test_answer).verdict_status()
        if test_status in ('runner_unavailable', 'internal_error', 'unavailable'):
            return JsonResponse({'error': 'Сервис выполнения временно недоступен', 'status': 'unavailable'}, status=503)
        if test_status != 'ok' and result['status'] == 'ok':
            result.update(status='error', fail_test=test_id)
        result['tests'].append(test_status)
        if test_status in ('realtime_limited', 'instructions_limited', 'output_limited', 'memory_limited'):
            result['tests'].extend(['skipped'] * (len(problem['tests']) - test_id - 1))
            break
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    status = result['status']
    if status == 'ok' and profile.course and profile.course.ok_ac_policy == 1:
        status = 'accepted'
    Submission.objects.create(problem=problem_db, code=code, user=request.user, status={v: k for k, v in Submission.STATUS_CHOICES}[status])
    if result['status'] == 'ok':
        from django.urls import reverse
        result['knowledge_url'] = reverse('knowledge_problem', args=[problem_db.urlname])
    return JsonResponse(result)
