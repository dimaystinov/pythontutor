from django.template import Context, Library, Node
from django.template.loader import get_template

from ..providers import providers_list


register = Library()


class SocialLoginNode(Node):
	def __init__(self, providers=None):
		self.providers = []

		all_providers = providers_list()

		if providers is None or len(providers) == 0:
			self.providers = all_providers
		else:
			for provider in providers:
				provider = provider.strip()
				if provider in all_providers:
					self.providers.append(provider)

	def render(self, context):
		return get_template('social_login.html').render(Context({'providers': self.providers}))


@register.tag('social-login')
def social_login(parser, token):
	providers = list(token.split_contents())[1:]
	return SocialLoginNode(providers)
