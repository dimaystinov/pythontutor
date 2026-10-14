"""Self-hosted settings. Secrets and deployment addresses come from the environment."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ['SECRET_KEY']
DEBUG = os.environ.get('DEBUG', '0').lower() in ('1', 'true', 'yes')
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1,[::1]').split(',')
CSRF_TRUSTED_ORIGINS = [s for s in os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',') if s]
DATABASE_PATH = os.environ.get('DATABASE_PATH', str(BASE_DIR / 'data' / 'db.sqlite3'))
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': DATABASE_PATH, 'OPTIONS': {'timeout': 30}}}
INSTALLED_APPS = ['django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes', 'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles', 'tutorial.apps.TutorialConfig']
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware', 'whitenoise.middleware.WhiteNoiseMiddleware', 'django.contrib.sessions.middleware.SessionMiddleware', 'django.middleware.common.CommonMiddleware', 'django.middleware.csrf.CsrfViewMiddleware', 'django.contrib.auth.middleware.AuthenticationMiddleware', 'tutorial.middleware.RequestQuotaMiddleware', 'django.contrib.messages.middleware.MessageMiddleware', 'django.middleware.clickjacking.XFrameOptionsMiddleware']
ROOT_URLCONF = 'pythontutor.urls'
WSGI_APPLICATION = 'pythontutor.wsgi.application'
TEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': [], 'APP_DIRS': True, 'OPTIONS': {'context_processors': ['django.template.context_processors.debug', 'django.template.context_processors.request', 'django.contrib.auth.context_processors.auth', 'django.contrib.messages.context_processors.messages', 'django.template.context_processors.static', 'tutorial.context_processors.execution']}}]
AUTH_PASSWORD_VALIDATORS = [{'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'}, {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'}, {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'}, {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'}]
LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'Europe/Moscow'
USE_I18N = True
USE_TZ = True
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'collected_static'
STORAGES = {'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'}, 'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'}}
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'
SERVER_PREFIX = '/'
ABSOLUTE_PREFIX = str(BASE_DIR) + '/'
DEFAULT_COURSE = '1534'
NEED_LOGIN = True
RUNNER_URL = os.environ.get('RUNNER_URL', 'http://runner:8081')
RUNNER_TOKEN = os.environ.get('RUNNER_TOKEN', '')
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', '0') == '1'
CSRF_COOKIE_SECURE = os.environ.get('CSRF_COOKIE_SECURE', '0') == '1'
SECURE_CONTENT_TYPE_NOSNIFF = True
DATA_UPLOAD_MAX_MEMORY_SIZE = 3 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024

SECURE_REDIRECT_EXEMPT = [r'^healthz/$', r'^health/$']
SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', '0') == '1'
SECURE_HSTS_SECONDS = int(os.environ.get('SECURE_HSTS_SECONDS', '0'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.environ.get('SECURE_HSTS_INCLUDE_SUBDOMAINS', '0') == '1'
SECURE_HSTS_PRELOAD = os.environ.get('SECURE_HSTS_PRELOAD', '0') == '1'
if os.environ.get('TRUST_PROXY_HEADERS', '0') == '1':
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

TUTOR_AI_API_KEY = os.environ.get('TUTOR_AI_API_KEY', '')
TUTOR_AI_BASE_URL = os.environ.get('TUTOR_AI_BASE_URL', '')
TUTOR_AI_MODEL = os.environ.get('TUTOR_AI_MODEL', '')
TUTOR_AI_FALLBACK_MODEL = os.environ.get('TUTOR_AI_FALLBACK_MODEL', '')
TUTOR_AI_DAILY_LIMIT = int(os.environ.get('TUTOR_AI_DAILY_LIMIT', '60'))

TUTOR_NVIDIA_API_KEY = os.environ.get('TUTOR_NVIDIA_API_KEY', '')
TUTOR_YANDEX_SPEECHKIT_API_KEY = os.environ.get('TUTOR_YANDEX_SPEECHKIT_API_KEY', '')
TUTOR_YANDEX_SPEECHKIT_VOICE = os.environ.get('TUTOR_YANDEX_SPEECHKIT_VOICE', 'marina')

TUTOR_TTS_PROVIDER = os.environ.get('TUTOR_TTS_PROVIDER', 'nvidia')

EXECUTION_MODE = os.environ.get('EXECUTION_MODE', 'browser')
