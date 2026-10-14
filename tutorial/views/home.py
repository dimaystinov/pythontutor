from operator import attrgetter

from django.shortcuts import render

from tutorial.models import Course, UserProfile
from tutorial.views import DEFAULT_COURSE


def home(request):
    raw_courses = [Course.objects.get(urlname=DEFAULT_COURSE)]
    lessons = {course: [lic for lic in sorted(course.lessonincourse_set.all(),
                        key=attrgetter('order'))]
                        for course in raw_courses}
    courses = list(lessons.items())
    return render(request, 'index.html', locals())
