from django.conf.urls import url

from .views import login_redirect, callback


urlpatterns = [
	url(r'^oauth/([^/]*)/?$', login_redirect, name='social_login'),
	url(r'^oauth/([^/]+)/callback$', callback, name='social_login-callback'),
]
