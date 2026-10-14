from django.views.decorators.http import require_POST
import logging
logger = logging.getLogger('pythontutor')

from django.http import HttpResponse, HttpResponseBadRequest


@require_POST
def log_user_action(request):
    # AJAX request
    # method: POST
    # params: action, data
    post = request.POST
    if 'action' in post and 'data' in post:
        if request.user.is_authenticated:
            user = request.user.username
        else:
            user = 'UNKNOWN'
        logger.info('user=%s, action=%s, data=%s', user, post['action'], post['data'])
        return HttpResponse('', content_type='application/json')
    else:
        logger.info(post)
        return HttpResponseBadRequest(str(post))
