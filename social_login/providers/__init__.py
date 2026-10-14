from importlib import import_module

from django.core.urlresolvers import reverse
from requests_oauthlib import OAuth1Session, OAuth2Session

from .. import logger


try:
	from ..config import PROVIDERS
except ImportError:
	PROVIDERS = {}
	logger.error('Cannot find social_login config file. Please, copy config.example.py as config.py and set up your OAuth credentials.')


provider_classes = None


def init_providers():
	global provider_classes

	provider_classes = {}

	for name in PROVIDERS:
		try:
			module = import_module(__package__ + '.' + name)
		except ImportError:
			logger.error(name + ' - no such OAuth provider implemented')
			continue

		provider_classes[name] = module.Provider


def providers_list():
	if provider_classes is None:
		init_providers()

	return list(provider_classes.keys())


def get_provider(name):
	global provider_classes

	if provider_classes is None:
		provider_classes = {}
		init_providers()


	if name not in PROVIDERS:
		return None

	try:
		clazz = provider_classes[name]
	except KeyError:
		return None

	return clazz()


class BaseProvider:
	def __init__(self, name):
		from ..views import current_request

		self.name = name
		self.config = PROVIDERS[name]

		self.callback_url = current_request.build_absolute_uri(reverse('social_login-callback', args=[name]))


	def get_auth_url(self):
		url, state = self.oauth.authorization_url(self.urls['authorization'])
		return url


class BaseProvider_OAuth1(BaseProvider):
	def __init__(self, name, authorization_url, request_token_url, access_token_url, scope=None):
		super().__init__(name)

		self.urls = {
			'request_token': request_token_url,
			'authorization': authorization_url,
			'access_token': access_token_url,
		}

		self.oauth = OAuth1Session(
			self.config['client_key'],
			self.config['client_secret'],
		)

	def _fetch_request_token(self):
		return self.oauth.fetch_request_token(self.urls['request_token'])

	def parse_callback_uri(self, uri):
		self._fetch_request_token()
		self.oauth.parse_authorization_response(uri)
		self._access_token = self.oauth.fetch_access_token(self.urls['access_token'])

	def get_auth_url(self):
		self._fetch_request_token()
		url = self.oauth.authorization_url(self.urls['authorization'], redirect_uri = self.callback_url)
		return url

class BaseProvider_OAuth2(BaseProvider):
	def __init__(self, name, authorization_url, get_token_url, scope=None):
		super().__init__(name)

		self.urls = {
			'authorization': authorization_url,
			'get_token': get_token_url,
		}

		self.oauth = OAuth2Session(
			self.config['client_id'],
			redirect_uri = self.callback_url,
			scope = scope,
		)

	def parse_callback_uri(self, uri):
		self._access_token = self.oauth.fetch_token(self.urls['get_token'], authorization_response=uri, client_secret = self.config['client_secret'])
