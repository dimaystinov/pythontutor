from operator import attrgetter

from django.conf import settings
from django.template import Context, Template


ABSOLUTE_PATH_TO_LESSONS = settings.ABSOLUTE_PREFIX + 'lessons/'


def get_sorted_lessons(course):
    return [lic.lesson for lic in sorted(course.lessonincourse_set.all(), 
                                         key=attrgetter('order'))]


def _parse_section_node(node, context, ids):
    sections = []

    i = 0

    content_section_started = False
    for subnode in node.nodelist:
        if subnode.__class__.__name__ == 'SectionNode':
            i += 1
            section_ids = ids + [i]

            content_section_started = False

            nested_sections = _parse_section_node(subnode, context, section_ids)
            sections.append({
                'id': '.'.join(map(str, section_ids)),
                'title': subnode.section_name,
                'subsections': nested_sections
            })
        else:
            text = subnode.render(context)
            if not content_section_started:
                sections.append({
                    'id': '.'.join(map(str, ids + [0])),
                    'title': '__text__',
                    'text': text
                })
                content_section_started = True
            else:
                sections[-1]['text'] += subnode.render(context)

    return sections

def _section_names(sections):
    names = []

    for section in sections:
        if section['title'] == '__text__':
            continue
        names.append((section['title'], section['id'], _section_names(section['subsections'])))

    return names

def load_lesson(lesson):
    filename = ABSOLUTE_PATH_TO_LESSONS + lesson.filename
    raw_lesson_content = open(filename, 'r', encoding='utf-8').read()

    lesson_content = '{% load lesson_content %}{% section \'__main__\' %}\n' + raw_lesson_content + '{% endsection %}'
    t = Template(lesson_content)

    context = Context()

    content = _parse_section_node(t.nodelist[1], context, [])

    return {
        'name': lesson.urlname,
        'title': lesson.title,
        'content': content,
        'sections': _section_names(content),
    }
