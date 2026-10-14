from . import BaseProvider_OAuth1
from ..user import OAuthUser


class TwitterOAuth(BaseProvider_OAuth1):
	def __init__(self):
		super().__init__(
			'twitter',
			access_token_url = 'https://api.twitter.com/oauth/access_token',
			authorization_url = 'https://api.twitter.com/oauth/authorize',
			request_token_url = 'https://api.twitter.com/oauth/request_token',
		)

	def fetch_user_info(self):
		json = self.oauth.get('https://api.twitter.com/1.1/account/verify_credentials.json?skip_status=true').json()

		return OAuthUser(
			'twitter-' + json['id_str'],
			email = None,
			name = json['name'],
			first_name = json['name'],
			last_name = None,
			gender = None,
			locale = json['lang'],
		)


Provider = TwitterOAuth
__all__ = ['Provider']
