from tutorial.enrollment import teacher_students
from collections import defaultdict

from django.shortcuts import render

from tutorial.lessons import get_sorted_lessons
from tutorial.models import Course, Lesson, Problem, Submission
from tutorial.problems import get_sorted_problems
from tutorial.utils import color_by_status, get_submission_color, sign_by_status


def get_users_and_best_submissions_for_problems(course, problems_loaded, allowed_users=None):
    users = set(allowed_users.filter(userprofile__course=course)) if allowed_users is not None else {user_profile.user for user_profile in course.userprofile_set.select_related().all()}
    submissions = {} # key: (user, problem)
    problems_db_objects = {problem['db_object'] for problem in problems_loaded}
    for submission in Submission.objects.select_related().filter(user__in=users, problem__in=problems_db_objects).order_by('time'):
        # We assume there are following submission statuses: 'ok', 'error', 'accepted',
        # 'coding_style_violation', 'ignored'.
        # for every (user, problem) we find chronologically first 'ok' submit.
        # if absent, we find chronologically last 'accepted' submit.
        # if absent, we find chronologically last 'error', 'coding_style_violation'
        #                                                  or 'ignored' submit.
        problem = submission.problem
        user = submission.user
        if (user, problem) in submissions:
            prev_submission = submissions[(user, problem)]
            if (prev_submission.get_status_display() not in ['ok', 'accepted']
                    or (prev_submission.get_status_display() == 'accepted' 
                    and submission.get_status_display() in ['accepted', 'ok'])):
                submissions[(user, problem)] = submission
        else:
            submissions[(user, problem)] = submission
    # import code; code.interact(local = locals())
    return users, submissions


def standings_for_lessons(request, course, lessons, navigation):
    problems = []

    for lesson in lessons:
        problems.extend(get_sorted_problems(lesson))

    users, submissions = get_users_and_best_submissions_for_problems(course, problems, teacher_students(request.user))

    user_scores = {user: [0, 0, 0] for user in users}  # [num_solved, rating, num_attempted]

    problems_num_solved = defaultdict(int)
    for (user, problem_db_object), submission in submissions.items():
        if submission.get_status_display() == 'ok':
            problems_num_solved[problem_db_object] += 1

    for (user, problem_db_object), submission in submissions.items():
        if submission.get_status_display() == 'ok':
            user_scores[user][0] += 1
            user_scores[user][1] += len(users) - problems_num_solved[problem_db_object] + 1
        else:
            user_scores[user][2] += 1

    users = list(users)
    users.sort(key=lambda x: ([-y for y in user_scores[x]], x.last_name, x.first_name))
    standings = {}
    for user in users:
        standings[user] = []
        for problem in problems:
            submission = submissions.get((user, problem['db_object']), None)
            if submission:
                color = color_by_status[submission.get_status_display()]
                sign = sign_by_status[submission.get_status_display()]
                standings[user].append((color, get_submission_color(color), sign, problem, submission))
            else:
                standings[user].append(('white', '#ffffff', '', problem, None))
    users = [(user, standings[user], user_scores[user][0], user_scores[user][1]) for user in users if user_scores[user][0] > 0]
    return render(request, 'standings.html', locals())


from tutorial.views import need_admin

@need_admin
def standings_for_lesson(request, course_urlname, lesson_urlname):
    course = Course.objects.get(urlname=course_urlname)
    lesson = Lesson.objects.get(urlname=lesson_urlname)
    navigation = dict(course=course, lesson=lesson)
    return standings_for_lessons(request, course, [lesson], navigation)


@need_admin
def standings_for_course(request, course_urlname):
    course = Course.objects.get(urlname=course_urlname)
    lessons = course.lessons.all()
    navigation = dict(course=course)
    return standings_for_lessons(request, course, lessons, navigation)
