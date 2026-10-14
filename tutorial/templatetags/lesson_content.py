# -*- coding: utf-8 -*-

import urllib.request, urllib.parse, urllib.error

from django.contrib.auth.models import User
from django.conf import settings
from django.template import Context, Library, Node, Template, TemplateSyntaxError
from django.template.loader import get_template

from tutorial.models import Problem, Submission
from tutorial.problems import load_problem


register = Library()



LESSON_IMG_ROOT = '/static/images/lesson_images/'


def _render_code_to_html(**kwargs):
    return get_template('code.html').render(kwargs)


class ProgramCodeNode(Node):
    def __init__(self, nodelist, executable=True, dataviz=True):
        self.nodelist = nodelist
        self.executable = executable
        self.dataviz = dataviz

    def render(self, context):
        context['input_data'] = ''
        code = self.nodelist.render(context).strip()
        input_data = context.get('input_data', '')

        return _render_code_to_html(**{
			'code': code,
            'input_data': input_data,
            'executable': self.executable,
            'dataviz': self.dataviz,
		})


@register.tag('program')
def highlight_program_code(parser, token):
    nodelist = parser.parse(('endprogram',))
    parser.delete_first_token()
    return ProgramCodeNode(nodelist, executable=True)


@register.tag('noprogram')
def highlight_program_code(parser, token):
    nodelist = parser.parse(('endnoprogram',))
    parser.delete_first_token()
    return ProgramCodeNode(nodelist, executable=False)


class InputDataNode(Node):
    def __init__(self, nodelist):
        self.nodelist = nodelist

    def render(self, context):
        input_data = self.nodelist.render(context).strip()
        context['input_data'] = input_data
        return ''


@register.tag('inputdata')
def add_input_data(parser, token):
    nodelist = parser.parse(('endinputdata',))
    parser.delete_first_token()
    return InputDataNode(nodelist)


class LessonNode(Node):
    def __init__(self, nodelist):
        self.nodelist = nodelist

    def render(self, context):
        context['sections'] = []
        content = self.nodelist.render(context)
        sections = context.get("sections", [])
        html = ['<div class="lesson">']
        if 'section_counter' in context:
            html.append('<div class="sections">Содержание:')
            for i, name in enumerate(sections):
                html.append('<br><a href="#{0}">{1}</a>'.format(i, name))
            html.append('</div>\n')
        html.append(content)
        html.append('</div>')
        return ''.join(html)


@register.tag('lesson')
def wrap_lesson(parser, token):
    nodelist = parser.parse(('endlesson',))
    parser.delete_first_token()
    return LessonNode(nodelist)


class WrapperNode(Node):
    def __init__(self, nodelist, html_before, html_after):
        self.nodelist = nodelist
        self.html_before = html_before
        self.html_after = html_after

    def render(self, context):
        return (Template(str(self.html_before)).render(context) + 
                self.nodelist.render(context) + 
                Template(str(self.html_after)).render(context))


class SectionNode(WrapperNode):
    def __init__(self, nodelist, section_name):
        super(SectionNode, self).__init__(nodelist, 
                '<h3><a name="{0}">' + '{0}'.format(section_name) + '</a></h3>', '')
        self.section_name = section_name

    def render(self, context):
        if 'section_counter' not in context:
            context['section_counter'] = 0
        self.html_before = self.html_before.format(context['section_counter'])
        context['section_counter'] += 1
        context['sections'].append(self.section_name)
        return super(SectionNode, self).render(context)


class SingleNode(Node):
    def __init__(self, html):
        self.html = html

    def render(self, context):
        return Template(str(self.html)).render(context)


def create_wrapper_tag(name, html_before, html_after):
    @register.tag(name)
    def wrapper_tag_func(parser, token):
        nodelist = parser.parse(('end' + name,))
        parser.delete_first_token()
        return WrapperNode(nodelist, html_before, html_after)   


def create_parameterized_wrapper_tag(name, html_before, html_after):
    @register.tag(name)
    def wrapper_tag_func(parser, token):
        params = token.split_contents()[1:]
        nodelist = parser.parse(('end' + name,))
        parser.delete_first_token()
        try:
            return WrapperNode(nodelist, html_before.format(*[str(p)[1:-1] for p in params]), html_after)   
        except IndexError:
            raise IndexError("tag '{0}' doesn't have a required parameter".format(name))


def create_parameterized_single_tag(name, html):
    @register.tag(name)
    def wrapper_tag_func(parser, token):
        params = token.split_contents()[1:]
        try:
            return SingleNode(html.format(*[str(p)[1:-1] for p in params]))
        except IndexError:
            raise IndexError("tag '{0}' doesn't have a required parameter".format(name))


@register.tag('section')
def wrapper_tag_func(parser, token):
    params = token.split_contents()[1:]
    nodelist = parser.parse(('endsection',))
    parser.delete_first_token()
    try:
        return SectionNode(nodelist, str(params[0])[1:-1])
    except IndexError:
        raise IndexError("tag 'section' doesn't have a required parameter")


create_wrapper_tag('input', '<p class="example_header">Пример входных данных:<br><pre>', '</pre></p>')
create_wrapper_tag('output', '<p class="example_header">Пример выходных данных:<br><pre>', '</pre></p>')
create_wrapper_tag('smartsnippet', '<p><div class="smartsnippet">', '</div></p>')
create_wrapper_tag('newword', '<u>', '</u>')
create_wrapper_tag('theorem', '<p><b>Теорема. </b>', '</p>')
create_wrapper_tag('proof', '<p><i>Доказательство. </i>', ' &#x25ae;</p>')

# create_parameterized_wrapper_tag('section', u'<h3>{0}</h3>', '')
create_parameterized_wrapper_tag('subsection', '<h4>{0}</h4>', '')

create_parameterized_single_tag('img', '<p align="center"><img src="' + LESSON_IMG_ROOT + '{0}" width="{1}%"></p>')
