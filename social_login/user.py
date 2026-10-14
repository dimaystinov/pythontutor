from django.contrib.auth.models import User, UserManager

from . import fire_event


class OAuthUser:
	def __init__(self, id, email, name, first_name=None, last_name=None, gender=None, locale=None, all_emails=None):
		self.id = id
		self.name = {
			'full': name,
			'first': first_name,
			'last': last_name,
		}
		self.email = email
		self.gender = gender
		self.locale = locale

		if self.name['full'] is None or self.name['full'] == '':
			self.name['full'] = self.name['first'] + ' ' + self.name['last']

		if all_emails == None:
			all_emails = []

		if email not in all_emails and email is not None:
			all_emails.append(email)

		self.all_emails = all_emails

	def __str__(self):
		return str(self.__dict__)


class OAuthUserAuthBackend:
	def authenticate(self, oauser):
		username = 'oauth-' + oauser.id

		try:
			user = User.objects.get(username=username)

		except User.DoesNotExist:
			user = User.objects.create_user(
				username,
				oauser.email,
				first_name = oauser.name['first'] or '',
				last_name = oauser.name['last'] or '',
			)
			user.is_active = True

			user.save()

			fire_event('register', user)

		fire_event('login', user)

		return user

	def get_user(self, user_id):
		try:
			return User.objects.get(pk=user_id)
		except:
			return None
