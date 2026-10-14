from django.contrib.auth import login, authenticate
from django.http import HttpResponse, HttpResponseNotFound
from django.shortcuts import redirect, render

from .helpers import SimpleLocalProxy
from .providers import get_provider


current_request = SimpleLocalProxy(None)


def login_redirect(request, provider_name):
	current_request._obj = request

	provider = get_provider(provider_name)

	if provider is None:
		return HttpResponseNotFound()

	return redirect(provider.get_auth_url())

def callback(request, provider_name):
	current_request._obj = request

	provider = get_provider(provider_name)

	if provider is None:
		return HttpResponseNotFound()

	if 'error' in request.GET:
		return HttpResponse('OAuth error: ' + request.GET['error'])

	# OAuthLib requires callback has been https, so https://www.example.com it's a little hack to workaround this
	provider.parse_callback_uri('https://www.example.com' + request.get_full_path())
	oauser = provider.fetch_user_info()

	siteuser = authenticate(oauser=oauser)
	login(request, siteuser)

	return render(request, 'login_finish.html', {'success': True})
