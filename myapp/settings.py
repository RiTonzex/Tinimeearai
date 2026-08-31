"""
Django settings for myapp project (ที่นี่มีอะไร - Check-in Web Application)
Optimized for Vercel Serverless Deployment & Mobile Excellence
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# โหลด Environment variables จากไฟล์ .env
load_dotenv(BASE_DIR / '.env', override=True)

# -----------------------------------------------------------------------------
# Security Settings
# -----------------------------------------------------------------------------
DEBUG = os.environ.get('DJANGO_DEBUG', 'True').lower() in ('true', '1', 'yes')

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'django-insecure-dev-tinimeearai-local-only-key-do-not-use-in-production'
    else:
        SECRET_KEY = 'django-insecure-auto-generated-fallback-key-change-me-in-production-env'

# -----------------------------------------------------------------------------
# Host & Domain Settings (Vercel & Production Safe)
# -----------------------------------------------------------------------------
# ALLOWED_HOSTS รองรับทุก Host บน Vercel และ Local เสมอ ป้องกัน Bad Request (400)
ALLOWED_HOSTS = ['*']

USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# CSRF Trusted Origins สำหรับ Vercel & Local
CSRF_TRUSTED_ORIGINS = [
    'https://*.vercel.app',
    'https://*.now.sh',
    'https://tinimeearai.vercel.app',
    'http://127.0.0.1:8000',
    'http://localhost:8000',
    'http://127.0.0.1',
    'http://localhost',
]
custom_trusted_origins = os.environ.get('CSRF_TRUSTED_ORIGINS')
if custom_trusted_origins:
    CSRF_TRUSTED_ORIGINS.extend([origin.strip() for origin in custom_trusted_origins.split(',') if origin.strip()])


# -----------------------------------------------------------------------------
# Application Definition
# -----------------------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Cloudinary Integration (Media Storage)
    'cloudinary_storage',
    'cloudinary',
    # Local Apps
    'checkin',
]


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # ให้บริการไฟล์ Static บน Vercel
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'myapp.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'checkin.context_processors.notifications_processor',
            ],
        },
    },
]

WSGI_APPLICATION = 'myapp.wsgi.application'

# -----------------------------------------------------------------------------
# Database Configuration (Postgres on Vercel/Neon/Supabase or SQLite locally)
# -----------------------------------------------------------------------------
DATABASE_URL = os.environ.get('DATABASE_URL')
is_vercel = os.environ.get('VERCEL') == '1'

if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=60,
            ssl_require=True,
        )
    }
    DATABASES['default']['DISABLE_SERVER_SIDE_CURSORS'] = True
else:
    db_path = Path('/tmp/db.sqlite3') if is_vercel else (BASE_DIR / 'db.sqlite3')
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': db_path,
        }
    }

# -----------------------------------------------------------------------------
# Password Validation
# -----------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# -----------------------------------------------------------------------------
# Internationalization
# -----------------------------------------------------------------------------
LANGUAGE_CODE = 'th-th'
TIME_ZONE = 'Asia/Bangkok'
USE_I18N = True
USE_TZ = True

# -----------------------------------------------------------------------------
# Static & Media Files (WhiteNoise + Cloudinary)
# -----------------------------------------------------------------------------
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static'] if (BASE_DIR / 'static').exists() else []
STATIC_ROOT = BASE_DIR / 'staticfiles_build' / 'static'

# WhiteNoise Configuration for Vercel Serverless
WHITENOISE_USE_FINDERS = True
WHITENOISE_MANIFEST_STRICT = False

MEDIA_URL = '/media/'
MEDIA_ROOT = Path('/tmp/media') if os.environ.get('VERCEL') == '1' else (BASE_DIR / 'media')

# -----------------------------------------------------------------------------
# Cloudinary Storage Configuration
# -----------------------------------------------------------------------------
CLOUDINARY_CLOUD_NAME = os.environ.get('CLOUDINARY_CLOUD_NAME')
CLOUDINARY_API_KEY = os.environ.get('CLOUDINARY_API_KEY')
CLOUDINARY_API_SECRET = os.environ.get('CLOUDINARY_API_SECRET')

CLOUDINARY_STORAGE = {
    'CLOUD_NAME': CLOUDINARY_CLOUD_NAME or 'dummy_cloud_name',
    'API_KEY': CLOUDINARY_API_KEY or 'dummy_key',
    'API_SECRET': CLOUDINARY_API_SECRET or 'dummy_secret',
}

USE_CLOUDINARY = bool(CLOUDINARY_CLOUD_NAME and CLOUDINARY_CLOUD_NAME != 'your_cloud_name')

STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

if USE_CLOUDINARY:
    DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
    STORAGES = {
        "default": {
            "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
else:
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }



# -----------------------------------------------------------------------------
# Production Security Headers (Auto-enabled when DEBUG = False)
# -----------------------------------------------------------------------------
# Reverse Proxy SSL Header for Vercel
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

if not DEBUG:
    SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'False').lower() in ('true', '1')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    X_FRAME_OPTIONS = 'DENY'


# Authentication URLs
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'post_list'
LOGOUT_REDIRECT_URL = 'login'

# Google OAuth 2.0 Credentials
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

