import json

from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render, get_object_or_404

from tutorial.models import Course, Lesson, Problem, Submission, ProblemInLesson
from django.urls import reverse
from tutorial.lessons import get_sorted_lessons, load_lesson
from tutorial.problems import get_sorted_problems, load_problem
from tutorial.views import DEFAULT_COURSE, need_login


def get_best_saved_code(user, problem_urlname):
    problem = Problem.objects.get(urlname=problem_urlname)

    submissions = Submission.objects.filter(user=user, problem=problem).order_by('-time')
    submission = None
    for s in submissions:
        if s.get_status_display() == 'ok':
            submission = s
            break

    if not submission and len(submissions) > 0:
        submission = submissions[0]

    return submission.code if submission else ''


@need_login
def problem_in_lesson(request, lesson_name, problem_name):
    problem_name = {'sherenga': 'lineup', 'queens': 'lists_queens'}.get(problem_name, problem_name)
    course = get_object_or_404(Course, urlname=DEFAULT_COURSE)
    lesson_db = get_object_or_404(Lesson, urlname=lesson_name, lessonincourse__course=course)

    lessons = course.lessonincourse_set.all()
    lesson = load_lesson(lesson_db)
    lesson_in_course = lesson_db.lessonincourse_set.get(course=course)

    problems = get_sorted_problems(lesson=lesson_db)
    for problem in problems:
        if request.user.is_authenticated:
            statuses = [submission.get_status_display() for submission
                    in Submission.objects.filter(user=request.user, problem=problem['db_object'])]
        else:
            statuses = []

        if 'ok' in statuses:
            problem['status'] = 'solved'
        elif 'accepted' in statuses:
            problem['status'] = 'accepted'
        elif 'error' in statuses:
            problem['status'] = 'unsolved'
        else:
            problem['status'] = ''

    problem_db = get_object_or_404(Problem, urlname=problem_name, probleminlesson__lesson=lesson_db)
    problem = load_problem(problem_db)

    ordered_tasks = list(ProblemInLesson.objects.filter(
        lesson__lessonincourse__course=course
    ).select_related('lesson', 'problem').order_by(
        'lesson__lessonincourse__order', 'lesson__lessonincourse__id', 'order', 'id'
    ))
    next_task = None
    for index, entry in enumerate(ordered_tasks):
        if entry.lesson_id == lesson_db.pk and entry.problem_id == problem_db.pk:
            if index + 1 < len(ordered_tasks):
                following = ordered_tasks[index + 1]
                next_task = {'url': reverse('problem_in_lesson', args=[following.lesson.urlname, following.problem.urlname]),
                             'title': load_problem(following.problem)['name']}
            break
    task_list_url = reverse('home')

    saved_code = get_best_saved_code(request.user, problem_name) if request.user.is_authenticated else ''

    from tutorial.beginner import guide
    beginner = guide(problem_name)
    from tutorial.task_help import task_hints as hints_for, task_figure
    task_hints = hints_for(problem_name)
    figure = task_figure(problem_name)
    if not saved_code and beginner:
        saved_code = beginner['code']

    tests_examples = []
    for test_input, test_output in zip(problem['tests'], problem['answers']):
        tests_examples.append({'input': test_input, 'output': test_output})

    from tutorial.knowledge import solved
    knowledge_unlocked = solved(request.user, problem=problem_db)
    ai_kind, ai_slug = 'problem', problem_name
    return render(request, 'problem.html', locals())
