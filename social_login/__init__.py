from logging import getLogger


logger = getLogger('social_login')


_callbacks = {
	'login': [],
	'register': [],
}

def sociallogin_callback(event):
	def decorator(func):
		_callbacks[event].append(func)
		return func

	return decorator

def fire_event(event, *args, **kwargs):
	result = True
	for func in _callbacks[event]:
		fres = func(*args, **kwargs)
		if fres is None:
			fres = True

		result &= fres

	return result
