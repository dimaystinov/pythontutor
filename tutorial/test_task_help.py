from io import StringIO
from pathlib import Path
from html.parser import HTMLParser
from django.conf import settings
from django.core.management import call_command
from django.test import TestCase, override_settings
from tutorial.models import ProblemInLesson
from tutorial.image_course import catalog
from tutorial.task_help import FIGURES

class HintsParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.hints=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='details' and attrs.get('class')=='task-hint':self.hints.append(attrs)

@override_settings(EXECUTION_MODE='browser')
class TaskHelpTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_course',stdout=StringIO())
        from django.contrib.auth.models import User
        cls.student=User.objects.create_user('help-test')
    def setUp(self):self.client.force_login(self.student)
    def test_every_task_has_two_closed_hints(self):
        urls=[f'/lessons/{p.lesson.urlname}/problems/{p.problem.urlname}/' for p in ProblemInLesson.objects.select_related('lesson','problem')]
        urls += [f'/images/{t["slug"]}/' for t in catalog()]
        self.assertEqual(len(urls),148)
        for url in urls:
            r=self.client.get(url);self.assertEqual(r.status_code,200,url)
            self.assertContains(r, "data-tutor-material")
            parser=HintsParser();parser.feed(r.content.decode())
            self.assertEqual(len(parser.hints),2,url)
            self.assertTrue(all('open' not in h for h in parser.hints),url)
            self.assertNotContains(r,'Во всех задачах считывайте входные данные')
            self.assertNotContains(r,'Напишите код самостоятельно: вставка')
    def test_figure_assets_exist_and_are_svg(self):
        from xml.etree import ElementTree
        for name,_ in FIGURES.values():
            path=Path(settings.BASE_DIR)/'tutorial/static/images/tasks'/f'{name}.svg'
            root=ElementTree.parse(path).getroot()
            self.assertTrue(root.tag.endswith('svg'))
    def test_minimal_assistant_has_no_manual_download_controls(self):
        r=self.client.get('/lessons/inout_and_arithmetic_operations/problems/rect_triangle_square/')
        self.assertNotContains(r,'id="tutor-load-model"')
        self.assertNotContains(r,'id="tutor-load-voice"')
        self.assertContains(r,'<details id="tutor-settings">')
