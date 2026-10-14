from django.conf import settings
from django.urls import include, re_path as url, path
from django.http import JsonResponse
from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView

from tutorial.views.home import home
from tutorial.views.lesson import lesson_in_course
from tutorial.views.log_events import log_user_action
from tutorial.views.problem import problem_in_lesson
from tutorial.views.profile import profile, register_user
from tutorial.views.standings import standings_for_course, standings_for_lesson
from tutorial.views.statistics import statistics
from tutorial.views.success_roadmap import success_roadmap, success_roadmap_last
from tutorial.views.teacher import teacher, teacher_group, teacher_student, join_group
from tutorial.views.tester import tester_submit
from tutorial.views.visualizer import execute, visualizer


admin.autodiscover()


from tutorial.views.images import image_index, image_task, image_run, image_submit, image_input, image_assignments

from tutorial.views.knowledge import knowledge_index, knowledge_problem, knowledge_image

from tutorial.views.assistant import assistant_chat, assistant_transcribe, assistant_speak

from tutorial.views import browser_execution, pwa

urlpatterns = [
    path('pwa/', pwa.dashboard, name='pwa'),
    path('sw.js', pwa.service_worker),
    path('manifest.webmanifest', pwa.manifest),
    path('pwa/download-manifest/', pwa.download_manifest),
    path('pwa/page/', pwa.public_page),
    path('browser/worker/', browser_execution.runtime_worker),
    path('browser/tests/<str:kind>/<slug:slug>/', browser_execution.tests),
    path('browser/submit/<str:kind>/<slug:slug>/', browser_execution.submit),
    path('assistant/speech/transcribe/', assistant_transcribe, name='assistant_transcribe'),
    path('assistant/speech/speak/<uuid:turn_id>/', assistant_speak, name='assistant_speak'),
    url(r'^assistant/(?P<kind>problem|lesson|image)/(?P<slug>[-a-zA-Z0-9_]+)/$', assistant_chat, name='assistant_chat'),
    url(r'^knowledge/$', knowledge_index, name='knowledge_index'),
    url(r'^knowledge/images/(?P<slug>[-a-zA-Z0-9_]+)/$', knowledge_image, name='knowledge_image'),
    url(r'^knowledge/(?P<slug>[-a-zA-Z0-9_]+)/$', knowledge_problem, name='knowledge_problem'),
    url(r'^images/$', image_index, name='image_index'),
    url(r'^images/assignments/$', image_assignments, name='image_assignments'),
    url(r'^images/(?P<slug>[-a-zA-Z0-9_]+)/$', image_task, name='image_task'),
    url(r'^images/(?P<slug>[-a-zA-Z0-9_]+)/run/$', image_run, name='image_run'),
    url(r'^images/(?P<slug>[-a-zA-Z0-9_]+)/submit/$', image_submit, name='image_submit'),
    url(r'^images/(?P<slug>[-a-zA-Z0-9_]+)/input/(?P<index>[0-9]+)/$', lambda request, slug, index: image_input(request, slug, int(index)), name='image_input'),
    url(r'^healthz?/$', lambda request: JsonResponse({'status': 'ok'}), name='health'),
    url(r'^old/$', home, name='old'),

    url(r'^admin/', admin.site.urls),

    url(r'^$', home, name="home"),

    url(r'^visualizer/execute/$', execute, name='visualizer_execute'),

    url(r'^visualizer/$', visualizer, name='visualizer'),

    url(r'^lessons/([^/]+)/$', lesson_in_course, name="lesson_in_course"),

    url(r'^lessons/([^/]+)/problems/([^/]+)/$', problem_in_lesson, name="problem_in_lesson"),

    url(r'^tester/submit/$', tester_submit, name='tester_submit'),

    url(r'^accounts/register/$', register_user, name='register'),

    url(r'^accounts/login/$', LoginView.as_view(template_name='login.html'), name='login'),
    url(r'^accounts/logout/$', LogoutView.as_view(), name='logout'),

    url(r'^profile/([^/]+)/$', profile, name="profile"),

    url(r'^statistics/$', statistics, name='statistics'),

    url(r'^log_user_action/$', log_user_action, name='log_user_action'),

    url(r'^teacher/$', teacher, name='teacher'),
    url(r'^teacher/groups/new/$', teacher_group, name='teacher_group_new'),
    url(r'^teacher/groups/(?P<pk>[0-9]+)/$', teacher_group, name='teacher_group_edit'),
    url(r'^teacher/students/new/$', teacher_student, name='teacher_student_new'),
    url(r'^teacher/students/(?P<pk>[0-9]+)/$', teacher_student, name='teacher_student_edit'),
    url(r'^join/(?P<code>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/$', join_group, name='join_group'),
    url(r'^success_roadmap/([^/]+)/$', success_roadmap, name='success_roadmap'),
    url(r'^success_roadmap_last/([^/]+)/$', success_roadmap_last, name='success_roadmap_last'),
    url(r'^standings/([^/]+)/$', standings_for_course, name='standings_for_course'),
    url(r'^standings/([^/]+)/lesson/([^/]+)/$', standings_for_lesson, name='standings_for_lesson'),
]
