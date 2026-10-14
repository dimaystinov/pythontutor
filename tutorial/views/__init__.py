# -*- coding: utf-8 -*-

from functools import wraps

from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect


DEFAULT_COURSE = settings.DEFAULT_COURSE


def dummy(request):
    return HttpResponse('dummy requested')


def need_login(function):
    @wraps(function)
    def need_login_wrapper(*args, **kwargs):
        request = args[0]
        if settings.NEED_LOGIN and not request.user.is_authenticated:
            return redirect(settings.SERVER_PREFIX + 'accounts/login/')
        return function(*args, **kwargs)
    return need_login_wrapper


def need_admin(function):
    @wraps(function)
    def need_admin_wrapper(*args, **kwargs):
        request = args[0]
        if not request.user.is_staff:
            return HttpResponseForbidden('Необходимо быть администратором'.encode('utf-8'))
        return function(*args, **kwargs)
    return need_admin_wrapper
