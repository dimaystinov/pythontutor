from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from tutorial.models import Course, Lesson, Problem, Submission, ProblemInLesson, StudyGroup

class SelfHostTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_course', stdout=StringIO())
        cls.user = User.objects.create_user('student', 'student@example.org', 'Correct-horse!29')
        cls.other = User.objects.create_user('other', password='Correct-horse!29')
        cls.teacher = User.objects.create_user('teacher', password='Correct-horse!29', is_staff=True)
        group = StudyGroup.objects.create(name='Test class', teacher=cls.teacher, course=Course.objects.get(urlname='1534'))
        for pupil in (cls.user, cls.other):
            pupil.userprofile.study_group = group
            pupil.userprofile.save()

    def test_seed_is_complete_and_preserves_progress(self):
        submission = Submission.objects.create(user=self.user, problem=Problem.objects.first(), code='print(1)', status=1)
        call_command('seed_course', stdout=StringIO())
        self.assertEqual(Problem.objects.count(), 134)
        self.assertEqual(Lesson.objects.count(), 15)
        self.assertEqual(ProblemInLesson.objects.count(), 134)
        self.assertEqual(User.objects.count(), 3)
        self.assertTrue(Submission.objects.filter(pk=submission.pk).exists())

    def test_all_lessons_and_problem_pages_render(self):
        self.client.force_login(self.user)
        for lesson in Lesson.objects.all():
            response = self.client.get(f'/lessons/{lesson.urlname}/')
            self.assertEqual(response.status_code, 200, lesson.urlname)
            for problem in lesson.problems.all():
                self.assertEqual(self.client.get(f'/lessons/{lesson.urlname}/problems/{problem.urlname}/').status_code, 200)
        for url in ['/', '/old/', '/visualizer/', '/healthz/']:
            self.assertEqual(self.client.get(url).status_code, 200)

    def test_original_and_archive_aliases_render(self):
        self.client.force_login(self.user)
        for slug in ['lineup', 'sherenga', 'lists_queens', 'queens']:
            self.assertEqual(self.client.get('/lessons/lists/problems/' + slug + '/').status_code, 200, slug)

    def test_registration_validation_and_login_logout(self):
        response = self.client.post('/accounts/register/', {'username':'new', 'email':'new@example.org', 'password':'Good-secret!934', 'confirm_password':'Good-secret!934', 'first_name':'New', 'last_name':'User'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(User.objects.get(username='new').userprofile.course.urlname, '1534')
        self.assertTrue(self.client.login(username='new', password='Good-secret!934'))
        self.assertEqual(self.client.get('/accounts/logout/').status_code, 405)
        self.assertEqual(self.client.post('/accounts/logout/').status_code, 302)
        self.client.logout()
        response = self.client.post('/accounts/register/', {'username':'weak', 'password':'123', 'confirm_password':'123'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='weak').exists())

    def test_privacy_teacher_and_profile_ownership(self):
        self.client.force_login(self.user)
        for url in ['/profile/other/', '/teacher/', '/statistics/', '/standings/1534/', '/success_roadmap/1/']:
            self.assertEqual(self.client.get(url).status_code, 403, url)
        self.assertEqual(self.client.post('/profile/other/', {'first_name':'Hacked'}).status_code,403)
        self.client.force_login(self.teacher)
        for url in ['/profile/other/', '/teacher/', '/statistics/', '/standings/1534/', '/success_roadmap/1/']:
            self.assertEqual(self.client.get(url).status_code,200,url)

    def test_csrf_required_for_submission_and_execution(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        for url in ['/tester/submit/', '/visualizer/execute/', '/accounts/logout/']:
            self.assertEqual(client.post(url, {}).status_code,403)

    @patch('tutorial.tester.execute_python')
    def test_submission_success_failure_and_runner_unavailable(self, execute):
        self.client.force_login(self.user)
        execute.return_value = SimpleNamespace(result='ok', stdout='6', stderr='')
        # A single known test avoids coupling this assertion to archived example values.
        with patch('tutorial.views.tester.load_problem', return_value={'tests':['1\n2\n3'], 'answers':['6']}):
            response = self.client.post('/tester/submit/', {'problem':'aplusbplusc','user_code':'print(6)'})
            self.assertEqual(response.json()['status'],'ok')
            self.assertEqual(Submission.objects.get().status,1)
            execute.return_value.stdout = '7'
            self.assertEqual(self.client.post('/tester/submit/', {'problem':'aplusbplusc','user_code':'print(7)'}).json()['status'],'error')
            execute.return_value.result = 'internal_error'
            self.assertEqual(self.client.post('/tester/submit/', {'problem':'aplusbplusc','user_code':'print(7)'}).status_code,503)
            self.assertEqual(Submission.objects.count(),2)

    def test_anonymous_submission_and_unknown_lesson(self):
        self.assertEqual(self.client.post('/tester/submit/', {'problem':'aplusbplusc','user_code':'print(6)'}).status_code,302)
        self.assertEqual(self.client.get('/lessons/missing/').status_code,404)

    def test_profile_password_change_keeps_session_and_rejects_mismatch(self):
        self.client.force_login(self.user)
        fields = {'first_name':'Changed', 'last_name':'Student', 'email':'updated@example.org', 'new_password':'Better-secret!432', 'new_password_repeated':'wrong'}
        self.client.post('/profile/student/', fields)
        self.user.refresh_from_db()
        self.assertNotEqual(self.user.first_name, 'Changed')
        fields['new_password_repeated'] = fields['new_password']
        self.client.post('/profile/student/', fields)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('Better-secret!432'))
        self.assertEqual(self.user.first_name,'Changed')
        self.assertEqual(self.client.get('/profile/student/').status_code,200)

    @patch('tutorial.tester.execute_python')
    def test_teacher_review_policy(self, execute):
        course = Course.objects.get(urlname='1534')
        course.ok_ac_policy = 1
        course.save()
        self.client.force_login(self.user)
        execute.return_value = SimpleNamespace(result='ok', stdout='6', stderr='')
        with patch('tutorial.views.tester.load_problem', return_value={'tests':[''], 'answers':['6']}):
            self.assertEqual(self.client.post('/tester/submit/', {'problem':'aplusbplusc','user_code':'print(6)'}).json()['status'],'ok')
        self.assertEqual(Submission.objects.get().status,2)

    @patch('tutorial.views.visualizer.execute_python')
    def test_visualizer_trace_and_syntax_error_response(self, execute):
        execute.return_value = SimpleNamespace(result='ok', stdout='1\n', stderr='', exception=None, trace=[{'event':'return', 'line':1, 'stdout':'1\n'}])
        response = self.client.post('/visualizer/execute/', {'user_script':'print(1)', 'input_data':''})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['trace'][0]['stdout'],'1\n')
        execute.return_value = SimpleNamespace(result='error', stdout='', stderr='', exception={'exception_type':'SyntaxError', 'exception_msg':'invalid syntax', 'line':99}, trace=[])
        self.assertEqual(self.client.post('/visualizer/execute/', {'user_script':'!', 'input_data':''}).status_code,200)

    def test_shared_rate_limit_and_window_reset(self):
        import hashlib
        from tutorial.models import RequestQuota
        key = hashlib.sha256(b'ip:127.0.0.1/accounts/login/').hexdigest()
        RequestQuota.objects.create(key=key, window=100, count=20)
        with patch('tutorial.middleware.time.time', return_value=6000):
            self.assertEqual(self.client.post('/accounts/login/', {}).status_code,429)
        with patch('tutorial.middleware.time.time', return_value=6060):
            self.assertEqual(self.client.post('/accounts/login/', {}).status_code,200)
        self.assertEqual(RequestQuota.objects.get(key=key).count,1)

    @patch('tutorial.tester.execute_python')
    def test_resource_limit_stops_remaining_tests(self, execute):
        self.client.force_login(self.user)
        execute.return_value = SimpleNamespace(result='realtime_limited', stdout='', stderr='')
        with patch('tutorial.views.tester.load_problem', return_value={'tests':[''] * 40, 'answers':['6'] * 40}):
            response = self.client.post('/tester/submit/', {'problem':'aplusbplusc','user_code':'while True: pass'})
        self.assertEqual(execute.call_count,1)
        self.assertEqual(response.json()['tests'],['realtime_limited'] + ['skipped'] * 39)


    @patch('tutorial.views.visualizer.execute_python')
    def test_execution_route_suffix_cannot_bypass_quota(self, execute):
        import hashlib
        from tutorial.models import RequestQuota
        key = hashlib.sha256(b'ip:127.0.0.1/visualizer/execute/').hexdigest()
        RequestQuota.objects.create(key=key, window=100, count=60)
        with patch('tutorial.middleware.time.time', return_value=6000):
            self.assertEqual(self.client.post('/visualizer/execute/', {'user_script':'print(1)', 'input_data':''}).status_code,429)
            self.assertEqual(self.client.post('/visualizer/execute/quota-bypass/', {'user_script':'print(1)', 'input_data':''}).status_code,404)
            self.assertEqual(self.client.get('/visualizer/unexpected/').status_code,404)
        execute.assert_not_called()

    @override_settings(SECURE_SSL_REDIRECT=True, SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO', 'https'))
    def test_trusted_https_proxy_redirect_and_health(self):
        self.assertEqual(self.client.get('/').status_code,301)
        self.assertEqual(self.client.get('/', HTTP_X_FORWARDED_PROTO='https').status_code,200)
        self.assertEqual(self.client.get('/', secure=True).status_code,200)
        for path in ['/healthz/', '/health/']:
            self.assertEqual(self.client.get(path).status_code,200)

    @override_settings(SECURE_SSL_REDIRECT=True, SECURE_PROXY_SSL_HEADER=None)
    def test_untrusted_forwarded_protocol_does_not_disable_redirect(self):
        self.assertEqual(self.client.get('/', HTTP_X_FORWARDED_PROTO='https').status_code,301)
