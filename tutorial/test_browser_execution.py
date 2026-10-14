import json
from unittest.mock import patch
from django.test import TestCase, override_settings
from django.contrib.auth.models import User
from django.core.management import call_command
from tutorial.models import Submission, ImageSubmission

@override_settings(EXECUTION_MODE='browser')
class BrowserExecutionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_course',verbosity=0)
        cls.user=User.objects.create_user('browser_student',password='qa-test-password')
    def setUp(self):
        self.client.force_login(self.user)
    @patch('tutorial.tester.execute_python',side_effect=AssertionError('Must not execute server Python'))
    def test_client_report_and_provenance(self, execute):
        from tutorial.problems import load_problem
        from tutorial.models import Problem
        task=load_problem(Problem.objects.get(urlname='aplusbplusc'))
        results=[{'result':'ok','stdout':answer} for answer in task['answers']]
        r=self.client.post('/browser/submit/problem/aplusbplusc/',data=json.dumps({'code':'print(1)','results':results}),content_type='application/json')
        self.assertEqual(r.status_code,200);self.assertEqual(r.json()['status'],'ok')
        self.assertEqual(Submission.objects.get().execution_source,'browser')
        results[0]['result']='wrong_answer'
        r=self.client.post('/browser/submit/problem/aplusbplusc/',data=json.dumps({'code':'print(1)','results':results}),content_type='application/json')
        self.assertEqual(r.json()['status'],'error')
        self.assertFalse(execute.called)
    def test_validation_auth_csrf_and_disabled_server(self):
        for url in ['/visualizer/execute/','/tester/submit/','/images/grayscale/run/','/images/grayscale/submit/']:
            self.assertEqual(self.client.post(url,{}).status_code,409)
        self.assertEqual(self.client.post('/browser/submit/problem/aplusbplusc/',data='{}',content_type='application/json').status_code,400)
        from django.test import Client
        secure=Client(enforce_csrf_checks=True);secure.force_login(self.user)
        self.assertEqual(secure.post('/browser/submit/problem/aplusbplusc/',{}).status_code,403)
        self.client.logout();self.assertEqual(self.client.get('/browser/tests/problem/aplusbplusc/').status_code,200)
    def test_test_data_and_sandbox(self):
        r=self.client.get('/browser/tests/problem/aplusbplusc/')
        self.assertEqual(r.status_code,200);self.assertIn('stdin',r.json()['tests'][0]);self.assertIn('answer',r.json()['tests'][0])
        r=self.client.get('/browser/tests/image/grayscale/');self.assertIn('expected',r.json()['tests'][0])
        r=self.client.get('/browser/worker/');self.assertIn("default-src 'none'",r['Content-Security-Policy'])

    def test_offline_public_snapshots_and_manifest(self):
        manifest=self.client.get('/pwa/download-manifest/').json()
        self.assertEqual(len([p for p in manifest['pages'] if '/problems/' in p]),134)
        self.assertIn('/browser/worker/',manifest['resources'])
        self.assertTrue(any(x.endswith('.wasm') for x in manifest['resources']))
        page=self.client.get('/pwa/page/',{'path':'/lessons/int_and_float/problems/last_digit/'})
        self.assertEqual(page.status_code,200)
        self.assertContains(page,'content="local"')
        self.assertContains(page,'Проверить решение на всех тестах')
        self.assertNotContains(page,'browser_student')
        for private in ['/admin/','/teacher/','/profile/browser_student/','/accounts/login/']:
            self.assertEqual(self.client.get('/pwa/page/',{'path':private}).status_code,404)
        app=self.client.get('/manifest.webmanifest').json()
        self.assertEqual(app['display'],'standalone')
        self.assertEqual(self.client.get('/sw.js')['Service-Worker-Allowed'],'/')
    def test_server_does_not_grade_client_output(self):
        r=self.client.post('/browser/submit/problem/aplusbplusc/',data=json.dumps({'code':'client code','results':[{'result':'ok','stdout':'not compared'}]*3}),content_type='application/json')
        self.assertEqual(r.json()['status'],'ok')
