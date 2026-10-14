"""Small-deployment throttling shared across Gunicorn workers via the database."""
import hashlib
import time
from django.conf import settings
from django.db.models import F
from django.http import JsonResponse
from tutorial.models import RequestQuota

class RequestQuotaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        server_run = request.path in ('/visualizer/execute/', '/tester/submit/') or (request.path.startswith('/images/') and request.path.endswith(('/run/', '/submit/')))
        if settings.EXECUTION_MODE == 'browser' and request.method == 'POST' and server_run:
            return JsonResponse({'error': 'Выполнение перенесено в браузер. Обновите страницу.'}, status=409)
        if request.method == 'POST' and request.path.startswith(('/images/', '/assistant/', '/browser/')):
            try:
                content_length = int(request.META.get('CONTENT_LENGTH') or 0)
            except ValueError:
                return JsonResponse({'error': 'Некорректный размер запроса.'}, status=400)
            if content_length > 3 * 1024 * 1024:
                return JsonResponse({'error': 'Запрос превышает 3 МиБ.'}, status=413)
        limits = {'/accounts/login/': 20, '/accounts/register/': 10, '/visualizer/execute/': 60, '/tester/submit/': 15}
        if request.path.startswith('/images/') and request.path.endswith(('/run/', '/submit/')):
            limits[request.path] = 15 if request.path.endswith('/submit/') else 30
        if request.path.startswith('/browser/submit/'):
            limits[request.path] = 15
        if request.path.startswith('/assistant/'):
            limits[request.path] = 8
        if request.method == 'POST' and request.path in limits:
            # Trust the socket address only; arbitrary X-Forwarded-For is spoofable.
            identity = f'user:{request.user.pk}' if request.user.is_authenticated else f'ip:{request.META.get("REMOTE_ADDR", "unknown")}'
            quota_path = ('/assistant/speech/transcribe/' if '/transcribe/' in request.path else '/assistant/speech/speak/' if '/speak/' in request.path else '/assistant/chat/') if request.path.startswith('/assistant/') else request.path
            key = hashlib.sha256((identity + quota_path).encode()).hexdigest()
            window = int(time.time()) // 60
            RequestQuota.objects.get_or_create(key=key, defaults={'window': window})
            RequestQuota.objects.filter(key=key).exclude(window=window).update(window=window, count=0)
            accepted = RequestQuota.objects.filter(key=key, window=window, count__lt=limits[request.path]).update(count=F('count') + 1)
            # Periodically discard inactive keys; no long-lived IP address inventory.
            if window % 10 == 0:
                RequestQuota.objects.filter(window__lt=window - 60).delete()
            if not accepted:
                response = JsonResponse({'error': 'Слишком много запросов. Повторите через минуту.'}, status=429)
                response['Retry-After'] = '60'
                return response
        return self.get_response(request)
