"""Import trusted archived teaching material, never historical accounts or submissions."""
import sqlite3
import json
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from tutorial.models import Course, Lesson, Problem, LessonInCourse, ProblemInLesson
from tutorial.problems import parse_file

class Command(BaseCommand):
    help = 'Idempotently seed all archived lessons and tasks; preserve users and progress.'

    @transaction.atomic
    def handle(self, **options):
        root = Path(settings.BASE_DIR)
        with sqlite3.connect(f'file:{root / "example.db"}?mode=ro', uri=True) as archive:
            archive.row_factory = sqlite3.Row
            courses, lessons, problems = {}, {}, {}
            for row in archive.execute('SELECT * FROM tutorial_course'):
                courses[row['id']], _ = Course.objects.update_or_create(urlname=row['urlname'], defaults={'title': row['title'], 'description': row['description'], 'ok_ac_policy': row['ok_ac_policy']})
            for row in archive.execute('SELECT * FROM tutorial_lesson'):
                if not (root / 'lessons' / row['filename']).is_file():
                    raise CommandError(f'Missing lesson: {row["filename"]}')
                lessons[row['id']], _ = Lesson.objects.update_or_create(urlname=row['urlname'], defaults={k: row[k] or '' for k in ('title', 'description', 'filename', 'external_contest_link')})
            # Keep the eleven core topics together, then the four archived extras.
            core = ['inout_and_arithmetic_operations', 'ifelse', 'int_and_float', 'for_loop', 'str', 'while', 'lists', 'functions', '2d_arrays', 'sets', 'dicts']
            rows = list(archive.execute('SELECT * FROM tutorial_lessonincourse ORDER BY "order"'))
            rows.sort(key=lambda r: core.index(lessons[r['lesson_id']].urlname) if lessons[r['lesson_id']].urlname in core else 100 + r['order'])
            for order, row in enumerate(rows, 1):
                LessonInCourse.objects.update_or_create(course=courses[row['course_id']], lesson=lessons[row['lesson_id']], defaults={'order': order})
            existing = {r['filename']: r for r in archive.execute('SELECT * FROM tutorial_problem')}
            test_count = 0
            for path in sorted((root / 'problems').rglob('*.txt')):
                filename = str(path.relative_to(root / 'problems'))
                try:
                    parsed = parse_file(path)
                except (ValueError, AssertionError) as exc:
                    raise CommandError(f'Invalid task {filename}: {exc}') from exc
                if not parsed.get('name') or not parsed.get('statement') or not parsed['tests']:
                    raise CommandError(f'Incomplete task {filename}')
                test_count += len(parsed['tests'])
                row = existing.get(filename)
                name = row['urlname'] if row else path.stem
                problem, _ = Problem.objects.update_or_create(urlname=name, defaults={'filename': filename})
                if row:
                    problems[row['id']] = problem
            for row in archive.execute('SELECT * FROM tutorial_probleminlesson ORDER BY "order"'):
                if row['problem_id'] in problems:
                    ProblemInLesson.objects.update_or_create(problem=problems[row['problem_id']], lesson=lessons[row['lesson_id']], defaults={'order': row['order']})
            folders = {'for': 'for_loop', 'inout': 'inout_and_arithmetic_operations'}
            for problem in Problem.objects.filter(probleminlesson__isnull=True):
                folder = Path(problem.filename).parent.name
                lesson = Lesson.objects.filter(urlname=folders.get(folder, folder)).first()
                if lesson is None:
                    raise CommandError(f'Cannot map task to lesson: {problem.filename}')
                last = ProblemInLesson.objects.filter(lesson=lesson).order_by('-order').first()
                ProblemInLesson.objects.create(problem=problem, lesson=lesson, order=last.order + 1 if last else 1)
        # Restore the publicly visible /old/ order while retaining archive-only tasks.
        order_file = root / 'knowledge' / 'upstream-order.json'
        if order_file.exists():
            for lesson_slug, slugs in json.loads(order_file.read_text()).items():
                lesson = Lesson.objects.get(urlname=lesson_slug)
                relations = list(ProblemInLesson.objects.filter(lesson=lesson).select_related('problem'))
                relations.sort(key=lambda r: slugs.index(r.problem.urlname) if r.problem.urlname in slugs else len(slugs) + r.order)
                for order, relation in enumerate(relations, 1):
                    relation.order = order
                    relation.save(update_fields=['order'])
        self.stdout.write(self.style.SUCCESS(f'Seeded {Course.objects.count()} courses, {Lesson.objects.count()} lessons, {Problem.objects.count()} problems, {test_count} tests. No accounts imported.'))
