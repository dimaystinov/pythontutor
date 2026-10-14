from . import BaseProvider_OAuth2
from ..user import OAuthUser


class GoogleOAuth(BaseProvider_OAuth2):
	def __init__(self):
		super().__init__(
			'google',
			authorization_url = 'https://accounts.google.com/o/oauth2/auth',
			get_token_url = 'https://accounts.google.com/o/oauth2/token',
			scope = [
				'https://www.googleapis.com/auth/userinfo.email',
				'https://www.googleapis.com/auth/userinfo.profile',
			]
		)

	def fetch_user_info(self):
		json = self.oauth.get('https://www.googleapis.com/oauth2/v1/userinfo').json()

		return OAuthUser(
			'google-' + json['id'],
			json['email'] if json['verified_email'] else None,
			json['name'],
			json['given_name'],
			json['family_name'],
			json['gender'],
			json['locale'],
		)


Provider = GoogleOAuth
__all__ = ['Provider']
