"""Configuration Django de développement pour l'équipe. Ne pas utiliser telle quelle en production."""
import os
import hashlib
import base64
import binascii
import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env', override=False)
ON_RENDER = os.getenv('RENDER') == 'true'
DEBUG = os.getenv('DJANGO_DEBUG', '0' if ON_RENDER else '1') == '1'
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'dev-only-change-this-key-before-deployment')
# Render generates 256 random bits encoded as Base64 (44 characters).
# Normalize only that format, preserving its entropy for Django's length check.
if ON_RENDER and len(SECRET_KEY) == 44:
    try:
        render_secret = base64.b64decode(SECRET_KEY, validate=True)
    except (ValueError, binascii.Error):
        render_secret = b''
    if len(render_secret) == 32:
        SECRET_KEY = hashlib.sha256(SECRET_KEY.encode()).hexdigest()
if not DEBUG and (len(SECRET_KEY) < 50 or SECRET_KEY.startswith('dev-only')):
    raise ImproperlyConfigured('Set a strong DJANGO_SECRET_KEY (at least 50 characters) for production.')

ALLOWED_HOSTS = [h.strip() for h in os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',') if h.strip()]

RENDER_HOSTNAME = os.getenv('RENDER_EXTERNAL_HOSTNAME', '').strip()
if RENDER_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_HOSTNAME)
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in os.getenv('DJANGO_CSRF_TRUSTED_ORIGINS', '').split(',') if origin.strip()]
if RENDER_HOSTNAME:
    CSRF_TRUSTED_ORIGINS.append('https://' + RENDER_HOSTNAME)

INSTALLED_APPS = [
    'django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes',
    'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles',
    'portal.apps.PortalConfig',
]
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
ROOT_URLCONF = 'config.urls'
TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'templates'], 'APP_DIRS': True,
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.debug',
        'django.template.context_processors.request',
        'django.contrib.auth.context_processors.auth',
        'django.contrib.messages.context_processors.messages',
        'portal.context_processors.catalog',
    ]},
}]
WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL:
    DATABASES = {'default': dj_database_url.parse(DATABASE_URL, conn_max_age=60, conn_health_checks=True)}
elif not DEBUG:
    raise ImproperlyConfigured('DATABASE_URL is required in production so profiles survive deployments.')
else:
    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Tunis'
USE_I18N = True
USE_TZ = True
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
DATA_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024  # corps JSON petit
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False  # nécessaire si le frontend doit lire le token AJAX
# Avant production : HTTPS, cookies Secure, DATABASE_URL, logs, CSP, rate limits.

LOGIN_URL = '/signin/'
FIREBASE_CONFIG = {
    'apiKey': os.getenv('FIREBASE_API_KEY', ''),
    'authDomain': os.getenv('FIREBASE_AUTH_DOMAIN', ''),
    'projectId': os.getenv('FIREBASE_PROJECT_ID', ''),
    'appId': os.getenv('FIREBASE_APP_ID', ''),
}
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

FIREBASE_SERVER_READY = bool(os.getenv('GOOGLE_APPLICATION_CREDENTIALS') or os.getenv('FIREBASE_USE_APPLICATION_DEFAULT_CREDENTIALS') == '1')

STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage' if not DEBUG else 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 3600
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    # Render terminates HTTPS and sets X-Forwarded-Proto itself.
    if ON_RENDER:
        SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_REDIRECT_EXEMPT = [r'^health/$']
