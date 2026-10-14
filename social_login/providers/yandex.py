from . import BaseProvider_OAuth2
from ..user import OAuthUser


class YandexOAuth(BaseProvider_OAuth2):
	def __init__(self):
		super().__init__(
			'yandex',
			authorization_url = 'https://oauth.yandex.ru/authorize',
			get_token_url = 'https://oauth.yandex.ru/token',
		)

	def fetch_user_info(self):
		json = self.oauth.get('https://login.yandex.ru/info').json()

		return OAuthUser(
			'yandex-' + json['id'],
			json['default_email'],
			json['display_name'],
			json['first_name'],
			json['last_name'],
			json['sex'],
			all_emails = json['emails'],
		)


Provider = YandexOAuth
__all__ = ['Provider']
