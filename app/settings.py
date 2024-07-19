import os
import logging
import pytz
from envparse import env
from dotenv import load_dotenv
from django.utils.translation import gettext_lazy as _

LOG_LEVEL = env.str('LOG_LEVEL', default='INFO')
DEBUG = LOG_LEVEL == 'DEBUG'
logging.basicConfig(level=LOG_LEVEL)

local_tz = pytz.timezone('Europe/Kiev')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

SECRET_KEY = env.str('SECRET_KEY')

API_ID = env.int('API_ID', default=0)
API_HASH = env.str('API_HASH', default='')

WEBAPP_HOST = env.str('WEBAPP_HOST', default='0.0.0.0')
WEBAPP_PORT = env.int('WEBAPP_PORT', default=8080)

WEBHOOK_DOMAIN = env.str('WEBHOOK_DOMAIN', default='example.com')
BASE_ADMIN_PATH = f'https://{WEBHOOK_DOMAIN}'

MYSQL_HOST = env.str('MYSQL_HOST', default='localhost')
MYSQL_PORT = env.int('MYSQL_PORT', default=3306)
MYSQL_PASSWORD = env.str('MYSQL_PASSWORD', default='')
MYSQL_USER = env.str('MYSQL_USER', default='')
MYSQL_DB = env.str('MYSQL_DB', default='')

BOT_ADMINS = env.list('BOT_ADMINS', default=0)

ALLOWED_HOSTS = [WEBHOOK_DOMAIN, '127.0.0.1', 'localhost']
CSRF_TRUSTED_ORIGINS = [f'https://{WEBHOOK_DOMAIN}']
BOT_DEVS = [BOT_ADMINS[0]]

USERBOT_PN_LIST = env.list('USERBOT_PN_LIST', default=[])
USERBOT_HOST_LIST = env.list('USERBOT_HOST_LIST', default=[])

HOST_FUNC_COUNT = 2


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django.contrib.humanize',

    'admin_reorder',
    'solo',

    'bot',
]

SITE_ID = 1

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.locale.LocaleMiddleware',

    'admin_reorder.middleware.ModelAdminReorder',
]

ROOT_URLCONF = 'app.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'templates'),
        ],
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

WSGI_APPLICATION = 'app.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': MYSQL_DB,
        'USER': MYSQL_USER,
        'PASSWORD': MYSQL_PASSWORD,
        'HOST': MYSQL_HOST,
        'PORT': MYSQL_PORT,
        'OPTIONS': {
            'charset': 'utf8mb4',
        },
    }
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

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


LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

CONSTANCE_BACKEND = 'constance.backends.database.DatabaseBackend'

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = '/static/'

STATICFILES_DIRS = (os.path.join(BASE_DIR, 'static'),)

MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

LOCALE_PATHS = (os.path.join(BASE_DIR, 'locale'),)


ADMIN_REORDER = [
    {
        'app': 'bot',
        'label': _('info'),
        'models': [
            {
                'label': _('a_userbots'),
                'model': 'bot.UserBot'
            },
            {
                'label': _('a_logs'),
                'model': 'bot.Log'
            },
            {
                'label': _('a_posts'),
                'model': 'bot.Post'
            },
            {
                'label': _('a_postchecks'),
                'model': 'bot.PostCheck'
            },
            {
                'label': _('a_statsviews'),
                'model': 'bot.StatsViews'
            },
        ]
    },
    {
        'app': 'bot',
        'label': _('management'),
        'models': [
            {
                'label': _('a_channels'),
                'model': 'bot.Channel'
            },
            {
                'label': _('a_limitations'),
                'model': 'bot.Limitation'
            },
            {
                'label': _('a_settings'),
                'model': 'bot.Settings'
            },
        ]
    },
]
