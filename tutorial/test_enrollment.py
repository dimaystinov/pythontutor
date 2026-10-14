import uuid
from django.contrib.auth.models import User
from django.test import TestCase, Client
from tutorial.models import Course, StudyGroup, Submission, Problem, ImageAssignment


class EnrollmentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.course = Course.objects.create(title='Python', urlname='1534')
        cls.other_course = Course.objects.create(title='Advanced', urlname='advanced')
        cls.teacher = User.objects.create_user('teacher_a', first_name='Первый', is_staff=True)
        cls.other_teacher = User.objects.create_user('teacher_b', first_name='Второй', is_staff=True)
        cls.admin = User.objects.create_superuser('admin', password='Unusual-secret-102!')
        cls.group = StudyGroup.objects.create(name='7А', teacher=cls.teacher, course=cls.other_course)
        cls.other_group = StudyGroup.objects.create(name='8Б', teacher=cls.other_teacher, course=cls.course)
        cls.student = User.objects.create_user('pupil_a', first_name='Анна', last_name='Своя')
        cls.other = User.objects.create_user('pupil_b', first_name='Борис', last_name='Чужой')
        for pupil, group in [(cls.student, cls.group), (cls.other, cls.other_group)]:
            profile = pupil.userprofile
            profile.study_group = group
            profile.save()

    def signup(self, name='new_pupil', code=None, **extra):
        data = dict(username=name, first_name='Иван', last_name='Ученик', password='Bright-owl-8762!', confirm_password='Bright-owl-8762!')
        if code is not None:
            data['invitation'] = str(code)
        data.update(extra)
        return self.client.post('/accounts/register/', data)

    def test_signup_enrolls_and_preserves_course_without_privileges(self):
        response = self.client.get('/accounts/register/', {'invite': self.group.invite_code})
        self.assertContains(response, 'Первый')
        self.assertContains(response, '7А')
        self.assertEqual(self.signup(code=self.group.invite_code, is_staff='1', teacher=self.other_teacher.pk).status_code, 302)
        pupil = User.objects.get(username='new_pupil')
        self.assertEqual(pupil.userprofile.study_group, self.group)
        self.assertEqual(pupil.userprofile.course, self.other_course)
        self.assertFalse(pupil.is_staff)
        self.assertTrue(pupil.check_password('Bright-owl-8762!'))
        self.client.force_login(self.teacher)
        self.assertContains(self.client.get('/teacher/'), 'new_pupil')

    def test_bad_closed_and_inactive_invites_reject_registration(self):
        for code in ['invalid', uuid.uuid4()]:
            self.assertEqual(self.signup(code=code).status_code, 200)
            self.assertFalse(User.objects.filter(username='new_pupil').exists())
        self.group.registration_open = False
        self.group.save()
        self.assertEqual(self.signup(code=self.group.invite_code).status_code, 200)
        self.group.registration_open = True
        self.group.save()
        self.teacher.is_active = False
        self.teacher.save()
        self.assertEqual(self.signup(code=self.group.invite_code).status_code, 200)
        self.assertFalse(User.objects.filter(username='new_pupil').exists())

    def test_optional_invitation_and_error_keeps_code(self):
        response = self.signup(code=self.group.invite_code, confirm_password='mismatch')
        self.assertContains(response, str(self.group.invite_code))
        self.assertFalse(User.objects.filter(username='new_pupil').exists())
        self.assertEqual(self.signup().status_code, 302)
        self.assertIsNone(User.objects.get(username='new_pupil').userprofile.study_group)

    def test_existing_user_must_confirm_and_cannot_switch_ownership(self):
        free = User.objects.create_user('free')
        self.client.force_login(free)
        path = f'/join/{self.group.invite_code}/'
        self.assertEqual(self.client.get(path).status_code, 200)
        free.userprofile.refresh_from_db()
        self.assertIsNone(free.userprofile.study_group)
        self.assertEqual(self.client.post(path).status_code, 302)
        free.userprofile.refresh_from_db()
        self.assertEqual(free.userprofile.study_group, self.group)
        self.client.post(f'/join/{self.other_group.invite_code}/')
        free.userprofile.refresh_from_db()
        self.assertEqual(free.userprofile.study_group, self.group)
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.post(path).status_code, 403)

    def test_group_create_rotate_close_and_ownership(self):
        self.client.force_login(self.teacher)
        response = self.client.post('/teacher/groups/new/', {'name':'Новая', 'course':self.course.pk, 'registration_open':'on', 'teacher':self.other_teacher.pk})
        self.assertEqual(response.status_code, 302)
        group = StudyGroup.objects.get(name='Новая')
        self.assertEqual(group.teacher, self.teacher)
        old = group.invite_code
        self.client.post(f'/teacher/groups/{group.pk}/', {'action':'rotate'})
        group.refresh_from_db()
        self.assertNotEqual(group.invite_code, old)
        self.client.post(f'/teacher/groups/{group.pk}/', {'name':'Новая', 'course':self.other_course.pk})
        group.refresh_from_db()
        self.assertFalse(group.registration_open)
        self.assertEqual(group.course, self.course)
        self.assertEqual(self.client.post(f'/teacher/groups/{self.other_group.pk}/', {'action':'rotate'}).status_code, 404)
        self.client.logout()
        self.assertEqual(self.signup(code=old).status_code, 200)

    def test_manual_add_edit_search_and_foreign_group_rejected(self):
        self.client.force_login(self.teacher)
        data = dict(username='manual', first_name='Мария', last_name='Ручная', password='Bright-owl-8762!', confirm_password='Bright-owl-8762!', study_group=self.other_group.pk)
        self.assertEqual(self.client.post('/teacher/students/new/', data).status_code, 200)
        self.assertFalse(User.objects.filter(username='manual').exists())
        data['study_group'] = self.group.pk
        self.assertEqual(self.client.post('/teacher/students/new/', data).status_code, 302)
        pupil = User.objects.get(username='manual')
        self.assertEqual(pupil.userprofile.study_group, self.group)
        self.assertFalse(pupil.is_staff)
        self.client.post(f'/teacher/students/{pupil.pk}/', dict(first_name='Новое', last_name='Имя', email='pupil@example.org', study_group=self.group.pk))
        pupil.refresh_from_db()
        self.assertEqual(pupil.first_name, 'Новое')
        self.assertTrue(pupil.check_password('Bright-owl-8762!'))
        self.assertContains(self.client.get('/teacher/', {'q':'pupil@example.org'}), 'manual')
        self.assertNotContains(self.client.get('/teacher/', {'q':'not-found'}), 'manual')
        self.assertEqual(self.client.get(f'/teacher/students/{self.other.pk}/').status_code, 404)
        self.assertEqual(self.client.post(f'/teacher/students/{self.other.pk}/', data).status_code, 404)

    def test_teacher_privacy_in_pages_admin_reports_and_assignments(self):
        self.client.force_login(self.teacher)
        self.assertNotContains(self.client.get('/teacher/'), 'pupil_b')
        self.assertEqual(self.client.get('/profile/pupil_b/').status_code, 403)
        self.assertEqual(self.client.get('/profile/pupil_a/').status_code, 200)
        response = self.client.get('/admin/tutorial/userprofile/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'pupil_a')
        self.assertNotContains(response, 'pupil_b')
        self.assertEqual(self.client.get(f'/admin/tutorial/userprofile/{self.other.userprofile.pk}/change/').status_code, 302)
        self.assertEqual(self.client.get('/admin/tutorial/studygroup/').status_code, 403)
        problem = Problem.objects.create(urlname='visible')
        Submission.objects.create(user=self.other, problem=problem, status=1, code='secret')
        response = self.client.get('/statistics/')
        self.assertEqual(response.context['submissions_in_last_day'], 0)
        ImageAssignment.objects.create(created_by=self.other_teacher, title='Private other assignment', task_slug='grayscale')
        self.assertNotContains(self.client.get('/images/assignments/'), 'Private other assignment')
        response = self.client.post('/images/assignments/', {'task_slug':'grayscale', 'title':'Wrong', 'assignee':self.other.pk})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(ImageAssignment.objects.filter(title='Wrong').exists())
        self.client.force_login(self.student)
        self.assertNotContains(self.client.get('/images/assignments/'), 'Private other assignment')
        self.client.force_login(self.other)
        self.assertContains(self.client.get('/images/assignments/'), 'Private other assignment')

    def test_admin_edit_names_group_and_course_sync(self):
        self.client.force_login(self.teacher)
        path = f'/admin/tutorial/userprofile/{self.student.userprofile.pk}/change/'
        data = dict(first_name='Анна', last_name='Обновлена', email='new@example.org', study_group=self.group.pk, course=self.course.pk, _save='Сохранить')
        self.assertEqual(self.client.post(path, data).status_code, 302)
        self.student.refresh_from_db()
        self.student.userprofile.refresh_from_db()
        self.assertEqual(self.student.last_name, 'Обновлена')
        self.assertEqual(self.student.userprofile.course, self.other_course)
        data['study_group'] = self.other_group.pk
        self.assertEqual(self.client.post(path, data).status_code, 200)
        self.student.userprofile.refresh_from_db()
        self.assertEqual(self.student.userprofile.study_group, self.group)
        self.client.force_login(self.admin)
        self.assertContains(self.client.get('/teacher/'), 'pupil_b')

    def test_student_cannot_manage_and_csrf_required(self):
        self.client.force_login(self.student)
        self.assertEqual(self.client.get('/join/' + '-' * 36 + '/').status_code, 404)
        for path in ['/teacher/', '/teacher/groups/new/', '/teacher/students/new/']:
            self.assertEqual(self.client.get(path).status_code, 403)
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.teacher)
        self.assertEqual(csrf.post('/teacher/groups/new/', {'name':'blocked'}).status_code, 403)
        csrf.force_login(self.student)
        self.assertEqual(csrf.post(f'/join/{self.group.invite_code}/').status_code, 403)
