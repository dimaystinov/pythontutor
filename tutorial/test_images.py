import base64
import io
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from PIL import Image
from tutorial.image_course import canonical_image
from tutorial.models import Course, ImageAssignment, ImageSubmission, StudyGroup


def png(color='red', size=(4, 3)):
    output = io.BytesIO()
    Image.new('RGB', size, color).save(output, 'PNG')
    return output.getvalue()


class ImageCourseTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.settings = override_settings(BASE_DIR=Path(self.temp.name))
        self.settings.enable()
        self.addCleanup(self.settings.disable)
        root = Path(self.temp.name) / 'image_course'
        root.mkdir()
        (root / 'input.png').write_bytes(png())
        (root / 'expected.png').write_bytes(png('blue'))
        self.task = {'slug':'color', 'title':'Color', 'statement':'Change color', 'starter':'import cv2', 'tests':[{'input':'input.png','expected':'expected.png'}]}
        (root / 'catalog.json').write_text(json.dumps([self.task]))
        Course.objects.create(urlname='1534', title='Python')
        self.user = User.objects.create_user('student', password='A-very-good-secret!')
        self.other = User.objects.create_user('other', password='A-very-good-secret!')
        self.teacher = User.objects.create_user('teacher', password='A-very-good-secret!', is_staff=True)
        group = StudyGroup.objects.create(name='Test class', teacher=self.teacher, course=Course.objects.get(urlname='1534'))
        self.user.userprofile.study_group = group
        self.user.userprofile.save()
        self.client.force_login(self.user)

    def test_upload_validation(self):
        for data in [b'bad file', b'x' * (2 * 1024 * 1024 + 1), png(size=(2001,2000))]:
            with self.assertRaises(ValueError):
                canonical_image(data)
        encoded = io.BytesIO()
        Image.new('RGB',(2,2)).save(encoded,'JPEG')
        self.assertTrue(canonical_image(encoded.getvalue()).startswith(b'\x89PNG'))

    @patch('tutorial.views.images.execute_python')
    def test_run_uploaded_image_and_no_submission(self, execute):
        execute.return_value = SimpleNamespace(result='ok', stdout='', stderr='', image=base64.b64encode(png('blue')).decode(), exception=None)
        response = self.client.post('/images/color/run/', {'code':'print(1)', 'image':SimpleUploadedFile('photo.png',png('green'),content_type='image/png')})
        self.assertEqual(response.status_code,200)
        self.assertTrue(response.json()['image'])
        self.assertEqual(base64.b64decode(execute.call_args.kwargs['image']), png('green'))
        self.assertEqual(ImageSubmission.objects.count(),0)
        self.assertEqual(self.client.post('/images/color/run/', {'code':'x', 'image':SimpleUploadedFile('bad.png',b'bad')}).status_code,400)

    @patch('tutorial.views.images.execute_python')
    def test_grade_uses_fixed_fixture_and_persists_progress(self, execute):
        execute.return_value = SimpleNamespace(result='ok', stdout='', stderr='', image=base64.b64encode(png('blue')).decode(), exception=None)
        response = self.client.post('/images/color/submit/', {'code':'solution', 'image':SimpleUploadedFile('spoof.png',png('green'))})
        self.assertEqual(response.json()['status'],'ok')
        self.assertEqual(base64.b64decode(execute.call_args.kwargs['image']),png())
        self.assertEqual(ImageSubmission.objects.get().user,self.user)
        execute.return_value.image = None
        self.assertEqual(self.client.post('/images/color/submit/', {'code':'no output'}).json()['status'],'error')
        execute.return_value.result = 'internal_error'
        self.assertEqual(self.client.post('/images/color/submit/', {'code':'infra error'}).status_code,503)
        self.assertEqual(ImageSubmission.objects.count(),2)

    def test_auth_csrf_and_assignment_access(self):
        anonymous = Client()
        self.assertEqual(anonymous.post('/images/color/run/', {'code':'x'}).status_code,302)
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.user)
        self.assertEqual(csrf.post('/images/color/submit/', {'code':'x'}).status_code,403)
        self.assertEqual(self.client.post('/images/assignments/', {'title':'x'}).status_code,403)
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.post('/images/assignments/', {'task_slug':'color','title':'Practice','assignee':self.user.pk,'description':'Do it'}).status_code,302)
        self.assertEqual(ImageAssignment.objects.get().created_by,self.teacher)
        self.assertEqual(self.client.post('/images/assignments/', {'task_slug':'missing','title':'Invalid'}).status_code,200)
        self.assertEqual(ImageAssignment.objects.count(),1)
        self.client.force_login(self.other)
        self.assertNotContains(self.client.get('/images/assignments/'),'Practice')
        self.client.force_login(self.user)
        self.assertContains(self.client.get('/images/assignments/'),'Practice')

    def test_pages_and_input(self):
        for url in ['/images/', '/images/color/', '/images/assignments/', '/images/color/input/0/']:
            self.assertEqual(self.client.get(url).status_code,200,url)
        self.assertEqual(self.client.get('/images/color/input/9/').status_code,404)
        self.assertEqual(self.client.get('/images/unknown/').status_code,404)
