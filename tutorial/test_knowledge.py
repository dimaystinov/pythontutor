from io import StringIO
from unittest.mock import patch
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from tutorial.models import Problem, Submission, ImageSubmission

ARTICLE = {'slug':'aplusbplusc','title':'Сумма трёх чисел','origin':'authored','summary':'Разбор',
    'recommended':{'title':'Линейный проход','code':'print("SECRET_REFERENCE")','explanation':'Пояснение','time_complexity':'O(1)','space_complexity':'O(1)'},
    'alternatives':[], 'pitfalls':[], 'sources':[]}

class KnowledgeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_course', stdout=StringIO())
        cls.user = User.objects.create_user('reader', password='Long-secret-941!')
        cls.other = User.objects.create_user('someone', password='Long-secret-942!')
        cls.problem = Problem.objects.get(urlname='aplusbplusc')

    @patch('tutorial.views.knowledge.article', return_value=ARTICLE)
    def test_only_own_success_unlocks_and_no_cache(self, _article):
        url = '/knowledge/aplusbplusc/'
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.user)
        Submission.objects.create(user=self.other,problem=self.problem,code='print(1)',status=1)
        Submission.objects.create(user=self.user,problem=self.problem,code='print(0)',status=0)
        response=self.client.get(url)
        self.assertEqual(response.status_code,403)
        self.assertNotContains(response,'SECRET_REFERENCE',status_code=403)
        self.assertIn('no-store',response['Cache-Control'])
        Submission.objects.create(user=self.user,problem=self.problem,code='<script>alert(1)</script>',status=2)
        response=self.client.get(url)
        self.assertContains(response,'SECRET_REFERENCE')
        self.assertNotContains(response,'<script>alert(1)</script>')
        self.assertContains(response,'&lt;script&gt;')
        self.assertIn('private',response['Cache-Control'])
        self.client.force_login(self.other)
        other_problem=Problem.objects.exclude(pk=self.problem.pk).first()
        self.assertEqual(self.client.get('/knowledge/'+other_problem.urlname+'/').status_code,403)

    @patch('tutorial.views.knowledge.article', return_value=ARTICLE)
    def test_image_gate_is_separate_from_classic(self, _article):
        self.client.force_login(self.user)
        Submission.objects.create(user=self.user,problem=self.problem,code='print(1)',status=1)
        self.assertEqual(self.client.get('/knowledge/images/grayscale/').status_code,403)
        ImageSubmission.objects.create(user=self.other,task_slug='grayscale',code='',status='ok')
        self.assertEqual(self.client.get('/knowledge/images/grayscale/').status_code,403)
        ImageSubmission.objects.create(user=self.user,task_slug='grayscale',code='',status='ok')
        self.assertEqual(self.client.get('/knowledge/images/grayscale/').status_code,200)
        self.assertEqual(self.client.get('/knowledge/images/no-such-task/').status_code,404)

    def test_files_are_not_static_and_arbitrary_slug_is_rejected(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get('/knowledge/not-a-problem/').status_code,404)
        self.assertEqual(self.client.get('/static/knowledge/solutions/aplusbplusc.json').status_code,404)
        self.assertEqual(self.client.get('/knowledge/../solutions/aplusbplusc.json').status_code,404)
