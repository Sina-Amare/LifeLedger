# settings.py

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
# Load SECRET_KEY from environment variables
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable not set.")


# SECURITY WARNING: don't run with debug turned on in production!
# Load DEBUG from environment variables, default to False if not set
DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 't')


# Load ALLOWED_HOSTS from environment variables
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')
if DEBUG:
    ALLOWED_HOSTS = ['127.0.0.1', 'localhost'] # Allow these during development


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites', # Add django.contrib.sites for email activation domain
    'accounts',
    'journal',
    'widget_tweaks',
    # 'tailwind', # Assuming you are not using Tailwind app based on your INSTALLED_APPS
    # 'theme',    # Assuming you are not using a separate theme app
]

# Assuming you are managing Tailwind directly without the Django Tailwind app
# If you are using the Django Tailwind app, uncomment the lines above and configure accordingly.
# TAILWIND_APP_NAME = 'theme' # Or your theme app name
# INTERNAL_IPS = [
#     "127.0.0.1",
# ]


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # 'django_browser_reload.middleware.BrowserReloadMiddleware', # For live reloading - uncomment if using
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

# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': os.getenv('DB_PORT'), # os.getenv returns string, ensure your DB adapter handles this or cast to int
    }
}

# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC' # Consider changing to your local timezone, e.g., 'Asia/Tehran'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom user model
AUTH_USER_MODEL = 'accounts.CustomUser'

# Redirect URLs
LOGIN_REDIRECT_URL = '/' # Redirect to home page after login
LOGOUT_REDIRECT_URL = '/' # Redirect to homepage after logout (Changed from 'accounts:login')

# AUTHENTICATION_BACKENDS: Specifies the authentication backend(s) to use.
AUTHENTICATION_BACKENDS = [
    'accounts.views.UsernameEmailBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# --- Email Settings ---
# Configure these settings to send emails.

# Load email backend from environment variable, default to console during development
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')

# SMTP settings (only needed if EMAIL_BACKEND is not console or dummy)
EMAIL_HOST = os.getenv('EMAIL_HOST')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587)) # Default SMTP TLS port
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() in ('true', '1', 't')
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'False').lower() in ('true', '1', 't')
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'webmaster@localhost') # Default sender email

# --- Site Settings (Needed for Email Activation Link Domain) ---
# Requires 'django.contrib.sites' in INSTALLED_APPS
SITE_ID = int(os.getenv('SITE_ID', 1)) # Default site ID is 1


# Email Debugging (Optional)
# if DEBUG:
#     import logging
#     logging.basicConfig(level=logging.DEBUG)

# Settings for media files (user-uploaded files)
MEDIA_ROOT = BASE_DIR / 'media' # Files will be stored in a 'media' directory at the project root
MEDIA_URL = '/media/' # URL prefix for accessing media files
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'journal': { # Your app's logger
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False, # <--- CHANGE THIS TO FALSE
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}
