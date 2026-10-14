from json import dumps

from . import BaseProvider_OAuth2
from ..user import OAuthUser


# VK's implementation of the OAuth2 server doesn't return the token_type when
# we want exchange temporary code on the API access token, so fix it.

# This is a violation of the OAuth2 specification - RFC 6749
# http://tools.ietf.org/html/rfc6749
# I wrote to customer support on this issue, but have not yet received a response.

def compliance_fix(session):
	def _compliance_fix(r):
		if 'application/json' in r.headers.get('content-type', {}) and r.status_code == 200:
			token = r.json()
		else:
			return r

		token['token_type'] = 'Bearer'
		r._content = dumps(token).encode('utf-8')

		return r

	session.register_compliance_hook('access_token_response', _compliance_fix)
	return session


class VKOAuth(BaseProvider_OAuth2):
	GENDERS = {
		0: None,
		1: 'female',
		2: 'male',
	}

	def __init__(self):
		super().__init__(
			'vk',
			authorization_url = 'https://oauth.vk.com/authorize',
			get_token_url = 'https://api.vk.com/oauth/access_token',
			scope = ['email'],
		)

		compliance_fix(self.oauth)

	def fetch_user_info(self):
		json = self.oauth.get('https://api.vk.com/method/users.get?uids=' + str(self._access_token['user_id']) + '&fields=uid,first_name,last_name,nickname,sex').json()
		json = json['response'][0]

		return OAuthUser(
			'vk-' + str(json['uid']),
			self._access_token['email'],
			json['nickname'],
			json['first_name'],
			json['last_name'],
			self.GENDERS[json['sex']],
		)


Provider = VKOAuth
__all__ = ['Provider']
