from tutorial.enrollment import teacher_students
from django.contrib.auth.models import User
from django.db.models import Count
from django.shortcuts import render

import datetime
from datetime import timedelta
from tutorial.models import Submission


from django.utils import timezone
from tutorial.views import need_admin

@need_admin
def statistics(request):
    visible_users = teacher_students(request.user)
    visible_submissions = Submission.objects.filter(user__in=visible_users)
    day_before = timezone.now() - timedelta(days=1)
    week_before = timezone.now() - timedelta(weeks=1)
    month_before = timezone.now() - timedelta(days=30)

    new_users_in_last_day = visible_users.filter(date_joined__gte=day_before).count()
    new_users_in_last_week = visible_users.filter(date_joined__gte=week_before).count()
    new_users_in_last_month = visible_users.filter(date_joined__gte=month_before).count()

    submissions_in_last_day = visible_submissions.filter(time__gte=day_before).count()
    submissions_in_last_week = visible_submissions.filter(time__gte=week_before).count()
    submissions_in_last_month = visible_submissions.filter(time__gte=month_before).count()

    ok_submissions_in_last_day = visible_submissions.filter(time__gte=day_before, status=1).count()
    ok_submissions_in_last_week = visible_submissions.filter(time__gte=week_before, status=1).count()
    ok_submissions_in_last_month = visible_submissions.filter(time__gte=month_before, status=1).count()

    active_users_in_last_day = (visible_submissions.filter(time__gte=day_before, status=1)
            .values('user').annotate(user_count=Count('user', distinct=True)).count())
    active_users_in_last_week = (visible_submissions.filter(time__gte=week_before, status=1)
            .values('user').annotate(user_count=Count('user', distinct=True)).count())
    active_users_in_last_month = (visible_submissions.filter(time__gte=month_before, status=1)
            .values('user').annotate(user_count=Count('user', distinct=True)).count())

    return render(request, 'statistics.html', locals())
