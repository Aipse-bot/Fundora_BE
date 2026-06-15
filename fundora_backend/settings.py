# fundora_backend/settings.py

from pathlib import Path
import os
import dj_database_url
from decouple import config
from datetime import timedelta

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
# Read from environment variable
SECRET_KEY = config("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
# Default to False if not set in environment
DEBUG = config("DEBUG", default=False, cast=bool)

# Read allowed hosts from environment variable, split by comma
# Example: ALLOWED_HOSTS=your-app.onrender.com,www.yourdomain.com
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="").split(',')


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
    'rest_framework',
    'corsheaders',
    'django_extensions',
    'rest_framework_simplejwt', # Make sure this is installed and listed
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware', # Should be early
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# CORS settings - Be specific for production
CORS_ALLOW_ALL_ORIGINS = False # Set to False for production
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000", # Example for a frontend running on localhost:3000
    "http://127.0.0.1:5501",
    "http://localhost:5501",
    # Add your Render domain if your frontend is also deployed there and needs to access the API
    # e.g., "https://your-frontend-app.onrender.com"
]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# CSRF settings - Be specific for production
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:5501",
    "http://127.0.0.1:5501",
    # Add your Render domain here too if needed
    # e.g., "https://your-app.onrender.com"
]

# Exempt API endpoints from CSRF if they don't use session auth
# This is often handled by JWTAuthentication, but good to keep if needed
# CSRF_EXEMPT_URLS = [
#     '/api/',
# ]


ROOT_URLCONF = 'fundora_backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'fundora_backend.wsgi.application'


# Database configuration using dj-database-url and environment variables
# Render provides DATABASE_URL automatically if you create a Postgres DB on Render
DATABASES = {
    'default': dj_database_url.config(
        default=config("DATABASE_URL", default=None), # Use config for DATABASE_URL too
        conn_max_age=600,
        ssl_require=True
    )
}
# If DATABASE_URL is not set, fall back to local SQLite for development
if DATABASES['default'] is None:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
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
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles' # This is where Django collects static files for deployment


# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer', # Useful for testing in browser
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        # Default to AllowAny if you want public APIs, or change to IsAuthenticated etc.
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication', # For browsable API / admin
    ),
}

# SIMPLE JWT settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=7),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': False,
    # 'SIGNING_KEY': SECRET_KEY, # This is automatically read from Django settings
}

# ML Service URL
ML_SERVICE_URL = config("ML_SERVICE_URL", default="https://fundora-ml-service.onrender.com") # Example, adjust if needed

# Media files (user uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media' # Corrected to remove redundancy