from django import template
from django import urls as urlresolvers
from django.template import Node


register = template.Library()

class IfPageIsNode(Node):
    def __init__(self, if_pages, nodelist):
        self.if_pages = if_pages
        self.nodelist = nodelist

    def render(self, context):
        try:
            resolved = urlresolvers.resolve(context.get('request').path)
            return self.nodelist.render(context) if resolved.url_name in self.if_pages else ''
        except:
            return ''

@register.tag
def ifpageis(parser, token):
    tag_name, *if_pages = token.split_contents()
    nodelist = parser.parse(('endif',))
    parser.delete_first_token()
    return IfPageIsNode(if_pages, nodelist)
