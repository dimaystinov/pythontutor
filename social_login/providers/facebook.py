from requests_oauthlib.compliance_fixes import facebook_compliance_fix

from . import BaseProvider_OAuth2
from ..user import OAuthUser


class FacebookOAuth(BaseProvider_OAuth2):
	def __init__(self):
		super().__init__(
			'facebook',
			authorization_url = 'https://www.facebook.com/v2.1/dialog/oauth',
			get_token_url = 'https://graph.facebook.com/v2.1/oauth/access_token',
		)

		self.oauth = facebook_compliance_fix(self.oauth)

	def fetch_user_info(self):
		json = self.oauth.get('https://graph.facebook.com/v2.1/me').json()

		return OAuthUser(
			'facebook-' + json['id'],
			json['email'] if 'email' in json else None,
			json['name'],
			json['first_name'],
			json['last_name'],
			json['gender'],
			json['locale'].split('_')[0],
		)


Provider = FacebookOAuth
__all__ = ['Provider']
