# -*- coding: utf-8 -*-

import urllib.request, urllib.parse, urllib.error

from django.contrib.auth.models import User
from django.conf import settings
from django.template import Context, Library, Node, TemplateSyntaxError
from django.template.loader import get_template
from django.utils.safestring import mark_safe

from tutorial.models import Problem, Submission
from tutorial.problems import load_problem


register = Library()



LESSON_IMG_ROOT = '/static/images/lesson_images/'


def _render_code_to_html(**kwargs):
    return get_template('code.html').render(kwargs)


class ProblemLinkNode(Node):
    def __init__(self, problem_ref):
        self.problem_ref = problem_ref

    def render(self, context):
        problem_urlname = context[self.problem_ref]['urlname']
        problem = load_problem(Problem.objects.get(urlname=problem_urlname))
        user = context['request'].user
        if user.is_authenticated:
            statuses = [submission.get_status_display() for submission 
                    in Submission.objects.filter(user=user, problem=problem['db_object'])]
        else:
            statuses = []
        if 'ok' in statuses:
            css_class = 'okProblemLink'
        elif 'error' in statuses:
            css_class = 'errorProblemLink'
        else:
            css_class = 'unsubmittedProblemLink'
        return '<span class="{0}">{1}</span>'.format(css_class, problem['name'])


@register.tag('problem_link')
def get_problem_link(parser, token):
    try:
        tag_name, problem_ref = token.split_contents()
    except ValueError:
        msg = '{0} tag requires a single argument'.format(token.split_contents()[0])
        raise TemplateSyntaxError(msg)
    return ProblemLinkNode(problem_ref)


class IdealSolutionNode(Node):
    def __init__(self, problem_ref):
        self.problem_ref = problem_ref

    def render(self, context):
        problem_urlname = context[self.problem_ref]['urlname']
        problem = load_problem(Problem.objects.get(urlname=problem_urlname))

        user = context['request'].user
        if not user.is_authenticated:
            return ''

        if not Submission.objects.filter(user=user, problem=problem['db_object'], status__in=[1, 2]).exists():
            return ''
        from django.urls import reverse
        from django.utils.html import format_html
        return format_html('<p><a href="{}">Рекомендуемое решение и другие способы</a></p>', reverse('knowledge_problem', args=[problem_urlname]))


@register.tag('ideal_solution')
def get_ideal_solution_link(parser, token):
    try:
        tag_name, problem_ref = token.split_contents()
    except ValueError:
        msg = '{0} tag requires a single argument'.format(token.split_contents()[0])
        raise TemplateSyntaxError(msg)
    return IdealSolutionNode(problem_ref)


def render_section(this, nesting_level=0):
    content = this.get('text', '')
    if 'subsections' in this:
        for subsection in this['subsections']:
            content += render_section(subsection, nesting_level + 1)
    else:
        if content.strip() == '':
            return ''
        else:
            return content

    return get_template('lesson_section.html').render({
        'id': this['id'],
        'title': this['title'],
        'nesting_level': nesting_level,
        'content': content,
    })

@register.filter
def lesson_content(lesson):
    content = ''

    for section in lesson['content']:
        content += render_section(section)

    return mark_safe(content)


def render_section_navitem(title, section_id, subsections):
    subsections_rendered = ''

    for subsection in subsections:
        subsections_rendered += render_section_navitem(*subsection)

    return get_template('lesson_section_navitem.html').render({
        'id': section_id,
        'title': title,
        'subsections': subsections_rendered,
    })

@register.filter
def lesson_navbar(lesson):
    navbar = ''

    for section in lesson['sections']:
        navbar += render_section_navitem(*section)

    return mark_safe(navbar)
