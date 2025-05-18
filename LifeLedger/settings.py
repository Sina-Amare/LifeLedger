# LifeLedger/LifeLedger/settings.py

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('SECRET_KEY', 'your-default-insecure-secret-key-for-dev-if-really-needed-0123456789abcdef')
DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1', 't')

ALLOWED_HOSTS_STRING = os.getenv('ALLOWED_HOSTS', '127.0.0.1,localhost')
ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS_STRING.split(',') if host.strip()]
if DEBUG and '127.0.0.1' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append('127.0.0.1')
if DEBUG and 'localhost' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append('localhost')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites', 
    'accounts.apps.AccountsConfig', 
    'journal.apps.JournalAppConfig', 
    'ai_services.apps.AiServicesConfig', 
    'widget_tweaks',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'LifeLedger.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'LifeLedger.wsgi.application'

DB_ENGINE_ENV = os.getenv('DB_ENGINE', 'django.db.backends.sqlite3')
DB_NAME_ENV = os.getenv('DB_NAME', str(BASE_DIR / 'db.sqlite3')) 

DATABASES = {
    'default': {
        'ENGINE': DB_ENGINE_ENV,
        'NAME': DB_NAME_ENV,
    }
}
if DB_ENGINE_ENV == 'django.db.backends.postgresql':
    DATABASES['default'].update({
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    })

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC' 
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [ BASE_DIR / "static", ]
STATIC_ROOT = BASE_DIR / "staticfiles_collected" 

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'accounts.CustomUser'
LOGIN_REDIRECT_URL = '/' 
LOGOUT_REDIRECT_URL = '/' 

AUTHENTICATION_BACKENDS = [
    'accounts.views.UsernameEmailBackend',
    'django.contrib.auth.backends.ModelBackend',
]

SITE_ID = int(os.getenv('SITE_ID', 1))

EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587)) 
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() in ('true', '1', 't')
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'False').lower() in ('true', '1', 't')
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'webmaster@localhost')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {'format': '{levelname} {asctime} {module} {message}','style': '{',},
        'verbose': {'format': '{levelname} {asctime} {name} {module} {process:d} {thread:d} {message}','style': '{',},
    },
    'handlers': {
        'console': {'level': 'DEBUG','class': 'logging.StreamHandler','formatter': 'simple',},
    },
    'loggers': {
        'django': {'handlers': ['console'],'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),'propagate': False,},
        'journal': {'handlers': ['console'],'level': 'DEBUG', 'propagate': False, },
        'accounts': {'handlers': ['console'],'level': 'DEBUG', 'propagate': False, },
        'ai_services': {'handlers': ['console'],'level': 'DEBUG', 'propagate': False, },
        'celery': {'handlers': ['console'],'level': 'DEBUG', 'propagate': False,}, # Changed celery log level to DEBUG
    },
    'root': {'handlers': ['console'],'level': 'INFO',},
}

# --- Celery Configuration ---
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json'] # Using only JSON for simplicity and security
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_ALWAYS_EAGER = False # Ensure this is False for actual async behavior

# Define a default queue, exchange, and routing key explicitly
CELERY_TASK_DEFAULT_QUEUE = 'lifelookup_default_queue'
CELERY_TASK_DEFAULT_EXCHANGE = 'lifelookup_default_exchange'
CELERY_TASK_DEFAULT_ROUTING_KEY = 'lifelookup_default_key'


# --- OpenRouter API Configuration ---
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
YOUR_SITE_URL = os.getenv('YOUR_SITE_URL', 'http://localhost:8000') 
YOUR_SITE_NAME = os.getenv('YOUR_SITE_NAME', 'LifeLedger') 

if not OPENROUTER_API_KEY:
    print("WARNING: OPENROUTER_API_KEY environment variable not set. AI features requiring it will not work.")
