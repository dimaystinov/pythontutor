import base64
import io
import uuid
from unittest.mock import patch
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client, override_settings
from django.core.management import call_command
from PIL import Image
from tutorial.models import Problem, Submission, TutorChatTurn, RequestQuota
from tutorial.ai_tutor import context_for, build_messages, TutorUnavailable


@override_settings(TUTOR_AI_API_KEY='private-test-key', TUTOR_AI_BASE_URL='https://provider.example/v1', TUTOR_AI_MODEL='test-model', TUTOR_NVIDIA_API_KEY='test-speech', TUTOR_YANDEX_SPEECHKIT_API_KEY='test-tts')
class AssistantTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_course', stdout=io.StringIO())
        cls.user=User.objects.create_user('learner')
        cls.other=User.objects.create_user('other')
        cls.problem=Problem.objects.get(urlname='electronic_watch')
        cls.url='/assistant/problem/electronic_watch/'

    def setUp(self):
        self.client.force_login(self.user)

    def ask(self, **extra):
        data={'question':'Подскажи следующий шаг', 'code':'n = int(input())', 'request_id':str(uuid.uuid4())}
        data.update(extra)
        return self.client.post(self.url, data)

    def test_context_server_gate(self):
        context=context_for(self.user,'problem','electronic_watch')
        self.assertFalse(context['solved']);self.assertNotIn('reviewed_editorial',context)
        Submission.objects.create(user=self.other,problem=self.problem,code='secret',status=1)
        self.assertFalse(context_for(self.user,'problem','electronic_watch')['solved'])
        Submission.objects.create(user=self.user,problem=self.problem,code='mine',status=1)
        context=context_for(self.user,'problem','electronic_watch')
        self.assertTrue(context['solved']);self.assertIn('reviewed_editorial',context)
        messages=build_messages(context,[], 'Вопрос','UNSAVED DRAFT')
        self.assertIn('UNSAVED DRAFT',messages[-1]['content'][0]['text'])

    @patch('tutorial.views.assistant.generate',return_value='Раздели число минут на 60.')
    def test_live_code_history_dedup_and_privacy(self, generate):
        key=str(uuid.uuid4())
        r=self.ask(request_id=key,code='fresh_code = 7')
        self.assertEqual(r.status_code,200)
        self.assertIn('fresh_code = 7',str(generate.call_args))
        self.assertEqual(self.ask(request_id=key).status_code,200)
        self.assertEqual(generate.call_count,1)
        self.assertEqual(TutorChatTurn.objects.filter(state='done').count(),1)
        history=self.client.get(self.url)
        self.assertEqual(len(history.json()['turns']),1)
        self.assertIn('no-store',history['Cache-Control'])
        self.assertNotContains(history,'private-test-key')
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url).json()['turns'],[])
        self.assertEqual(self.client.post(f'/assistant/speech/speak/{key}/').status_code,404)

    @patch('tutorial.views.assistant.generate',side_effect=TutorUnavailable('Попробуйте позже'))
    def test_failure_is_not_an_answer(self, generate):
        self.assertEqual(self.ask().status_code,503)
        self.assertEqual(TutorChatTurn.objects.get().state,'failed')
        self.assertEqual(self.client.get(self.url).json()['turns'],[])

    @patch('tutorial.views.assistant.generate',return_value='Подсказка')
    def test_limits_csrf_auth_and_cross_task_id(self, generate):
        self.assertEqual(self.ask(question='x'*3001).status_code,400)
        self.assertEqual(self.ask(code='x'*12001).status_code,400)
        self.assertEqual(self.ask(request_id='bad').status_code,400)
        key=str(uuid.uuid4());self.ask(request_id=key)
        self.assertEqual(self.client.post('/assistant/problem/aplusbplusc/',{'request_id':key,'question':'Другое'}).status_code,409)
        with override_settings(TUTOR_AI_DAILY_LIMIT=1):
            self.assertEqual(self.ask().status_code,429)
        csrf=Client(enforce_csrf_checks=True);csrf.force_login(self.user)
        self.assertEqual(csrf.post(self.url,{'question':'x'}).status_code,403)
        self.assertEqual(Client().get(self.url).status_code,302)

    @patch('tutorial.views.assistant.generate',return_value='Вижу картинку')
    def test_images_and_material_context(self, generate):
        out=io.BytesIO();Image.new('RGB',(4,4),'red').save(out,'PNG')
        r=self.ask(image=SimpleUploadedFile('sample.png',out.getvalue(),content_type='image/png'))
        self.assertEqual(r.status_code,200)
        self.assertEqual(generate.call_args.args[0][-1]['content'][-1]['type'],'input_image')
        self.assertNotIn('data:image',TutorChatTurn.objects.get().question)
        self.assertEqual(self.ask(image=SimpleUploadedFile('bad.png',b'not image')).status_code,400)
        self.assertEqual(self.client.get('/assistant/lesson/ifelse/').status_code,200)
        self.assertEqual(self.client.get('/assistant/image/grayscale/').status_code,200)
        self.assertEqual(self.client.get('/assistant/problem/missing/').status_code,404)

    @patch('tutorial.speech.transcribe',return_value='Как посчитать часы?')
    @patch('tutorial.speech.synthesize',return_value=b'RIFFtestaudio')
    def test_voice_endpoints(self,synthesize,transcribe):
        r=self.client.post('/assistant/speech/transcribe/',{'audio':SimpleUploadedFile('audio.pcm',b'\0\0'*16000)})
        self.assertEqual(r.status_code,200);self.assertEqual(r.json()['text'],'Как посчитать часы?')
        self.assertEqual(self.client.post('/assistant/speech/transcribe/',{}).status_code,400)
        turn=TutorChatTurn.objects.create(user=self.user,kind='problem',slug='electronic_watch',request_id=uuid.uuid4(),question='Q',answer='Готовый ответ',state='done')
        r=self.client.post(f'/assistant/speech/speak/{turn.request_id}/',{'text':'Arbitrary ignored'})
        self.assertEqual(r['Content-Type'],'audio/wav');synthesize.assert_called_once_with('Готовый ответ')
        self.assertIn('no-store',r['Cache-Control'])

    def test_pages_have_panel_without_credentials(self):
        for path in ['/lessons/inout_and_arithmetic_operations/problems/electronic_watch/','/lessons/ifelse/','/images/grayscale/']:
            r=self.client.get(path);self.assertContains(r,'tutor-panel');self.assertNotContains(r,'private-test-key')

    @patch('tutorial.ai_tutor.requests.Session')
    def test_provider_response_and_fallback(self, session):
        from tutorial.ai_tutor import generate
        response=session.return_value.__enter__.return_value.post.return_value
        response.__enter__.return_value=response
        response.status_code=200
        response.iter_content.return_value=[b'{"status":"completed","output":[{"type":"message","content":[{"type":"output_text","text":"hello"}]}]}']
        self.assertEqual(generate([{'role':'user','content':'test'}]),'hello')
        call=session.return_value.__enter__.return_value.post.call_args
        self.assertFalse(call.kwargs['allow_redirects']);self.assertFalse(call.kwargs['json']['store'])
        response.status_code=401
        with self.assertRaises(TutorUnavailable):generate([])

    @patch('tutorial.views.assistant.generate',return_value='Answer')
    def test_quota_shared_across_tasks(self, generate):
        for i in range(8):
            path=self.url if i%2 else '/assistant/problem/aplusbplusc/'
            self.assertEqual(self.client.post(path,{'question':'q','request_id':str(uuid.uuid4())}).status_code,200)
        self.assertEqual(self.ask().status_code,429)

    @patch('riva.client.Auth', side_effect=RuntimeError('provider credentials redacted'))
    def test_speech_connection_failure_is_safe(self, auth):
        from tutorial.speech import transcribe, synthesize_nvidia
        for action in [lambda: transcribe(b'\0\0'*16000), lambda: synthesize_nvidia('Привет')]:
            with self.assertRaises(TutorUnavailable) as error:
                action()
            self.assertNotIn('credentials', str(error.exception))

    @patch('riva.client.Auth')
    @patch('riva.client.SpeechSynthesisService')
    def test_speech_chunks_and_valid_wav(self, service, auth):
        import wave
        from tutorial.speech import synthesize_nvidia
        service.return_value.synthesize.return_value.result.return_value.audio = b'\0\0'*240
        wav = synthesize_nvidia('Это предложение для проверки. '*35)
        self.assertGreater(service.return_value.synthesize.call_count, 1)
        for call in service.return_value.synthesize.call_args_list:
            self.assertLessEqual(len(call.args[0]), 450)
        with wave.open(io.BytesIO(wav)) as stream:
            self.assertEqual(stream.getframerate(), 24000)
            self.assertEqual(stream.getsampwidth(), 2)
            self.assertGreater(stream.getnframes(), 0)
        auth.return_value.channel.close.assert_called_once()
