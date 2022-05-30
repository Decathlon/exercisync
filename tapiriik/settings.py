import os
import sys
from datetime import datetime
from django.utils.translation import ugettext_lazy as _
import logging
import logging.handlers
import io

# Django settings for tapiriik project.

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEBUG = True

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

ALLOWED_HOSTS = ["tapiriik.com", ".tapiriik.com", "localhost"]

USE_X_FORWARDED_HOST = True

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

LANGUAGES = (
    ('en', _('English')),
    ('fr', _('French')),
    ('ru', _('Russian')),
)

LOCALE_PATHS = (
    os.path.join(BASE_DIR, 'tapiriik/locale'),
)

#LOG_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), os.pardir)) + '/logs'
LOG_PATH = os.path.abspath("logs")

logging.basicConfig(
    filename=os.path.abspath("logs") + '/log_global.log',
    level=logging.INFO,
    format='%(asctime)s|%(levelname)s\t|%(message)s |%(funcName)s in %(filename)s:%(lineno)d',
    datefmt='%Y-%m-%d %H:%M:%S',
)

_GLOBAL_LOGGER = logging.getLogger()
_GLOBAL_LOGGER.setLevel(logging.INFO)
logging_console_handler = logging.StreamHandler(io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8'))
logging_console_handler.setLevel(logging.INFO)
logging_console_handler.setFormatter(logging.Formatter('%(asctime)s|%(levelname)s\t|%(message)s |%(funcName)s in %(filename)s:%(lineno)d','%Y-%m-%d %H:%M:%S'))
_GLOBAL_LOGGER.addHandler(logging_console_handler)

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/var/www/example.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://example.com/media/", "http://media.example.com/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/var/www/example.com/static/"
STATIC_ROOT = 'C:/wamp/www/tapiriik/tapiriik/static/'

# URL prefix for static files.
# Example: "http://example.com/static/", "http://static.example.com/"
STATIC_URL = '/static/'

VUE_DEV_URL = 'https://cdn.jsdelivr.net/npm/vue@2.6.14/dist/vue.js'
VUE_PROD_URL = 'https://cdn.jsdelivr.net/npm/vue@2.6.14/dist/vue.min.js'
VUE_URL = VUE_PROD_URL if DEBUG == False else VUE_DEV_URL

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    #os.path.join(BASE_DIR, 'assets'), 
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'pipeline.finders.PipelineFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

STATICFILES_STORAGE = 'pipeline.storage.PipelineCachedStorage'

# PIPELINE_JS = {
#     'tapiriik-js': {
#         'source_filenames': (
#           'js/jquery.address-1.5.min.js',
#           'js/tapiriik.js',
#         ),
#         'output_filename': 'js/tapiriik.min.js',
#     },
#     'tapiriik-user-js': {
#         'source_filenames': (
#           'js/jstz.min.js',
#           'js/tapiriik-ng.js',
#         ),
#         'output_filename': 'js/tapiriik-user.min.js',
#     }
# }

# PIPELINE_CSS = {
#     'tapiriik-css': {
#         'source_filenames': (
#           'css/style.css',
#         ),
#         'output_filename': 'css/style.min.css',
#     },
# }

PIPELINE = {
    'CSS_COMPRESSOR': 'pipeline.compressors.cssmin.CSSMinCompressor',
    'JS_COMPRESSOR': 'pipeline.compressors.jsmin.JSMinCompressor',
    'DISABLE_WRAPPER': True,
}

# Make this unique, and don't share it with anybody.
# and yes, this is overriden in local_settings.py
SECRET_KEY = 'vag26gs^t+_y0msoemqo%_5gb*th(i!v$l6##bq9tu2ggcsn13'

# In production, webservers must have only the public key
CREDENTIAL_STORAGE_PUBLIC_KEY = b"NotTheRealKeyFYI"
CREDENTIAL_STORAGE_PRIVATE_KEY = None

MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'tapiriik.web.startup.Startup',
    'tapiriik.web.startup.ServiceWebStartup',
    'tapiriik.auth.SessionAuth',
    'tapiriik.device_support.DeviceSupportMiddleware',
    'tapiriik.user_origin.UserOriginMiddleware'
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"  # file-based sessions on windows are terrible

ROOT_URLCONF = 'tapiriik.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'tapiriik.wsgi.application'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'tapiriik.web.views.ab_experiment_context',
                'tapiriik.web.context_processors.user',
                'tapiriik.web.context_processors.config',
                'tapiriik.web.context_processors.js_bridge',
                'tapiriik.web.context_processors.stats',
                'tapiriik.web.context_processors.providers',
                'tapiriik.web.context_processors.celebration_mode',
                'tapiriik.web.context_processors.device_support',
                'tapiriik.web.context_processors.background_use',
                'tapiriik.web.context_processors.vue_link',
                'tapiriik.web.context_processors.decat_club_env_link',
                'tapiriik.web.context_processors.is_user_from_dkt_club',
                'django.template.context_processors.static',
                'django.template.context_processors.request',
                'django.template.context_processors.i18n'
            ],
            'debug': DEBUG
        },
    },
]


INSTALLED_APPS = (
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'tapiriik.web',
    'pipeline'
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'console': {
            'level': 'ERROR',
            'class': 'logging.StreamHandler'
        },
        'logfile': {
            'level': 'ERROR',
            'class': 'logging.handlers.WatchedFileHandler',
            'filename': '/tapiriik/logs/app.log'
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins', 'console', 'logfile'],
            'level': 'ERROR',
            'propagate': True,
        },
        'django': {
            'handlers': ['logfile'],
            'level': 'ERROR',
            'propagate': False,
        },
    }
}


TEST_RUNNER = 'django.test.runner.DiscoverRunner'
#'tapiriik.testing.MongoDBTestRunner'

MONGO_HOST_API = "localhost"
MONGO_REPLICA_SET = None
MONGO_CLIENT_OPTIONS = {}
MONGO_FULL_WRITE_CONCERN = 1
POSTGRES_HOST_API = "postgresql://user:[password]@localhost:5432/database"

REDIS_HOST = "localhost"
REDIS_CLIENT_OPTIONS = {}

WEB_ROOT = 'http://localhost:8000'

PP_WEBSCR = "https://www.sandbox.paypal.com/cgi-bin/webscr"
PP_BUTTON_ID = "XD6G9Z7VMRM3Q"
PP_RECEIVER_ID = "NR6NTNSRT7NDJ"
PAYMENT_AMOUNT = 2
PAYMENT_SYNC_DAYS = 365.25
PAYMENT_CURRENCY = "USD"


# Celebration mode config
# Because why not, I'm waiting for my account to get to the front of the sync queue.

CELEBRATION_MODES = {
    (
        datetime(day=1, month=1, year=datetime.now().year, hour=0, minute=0),
        datetime(day=1, month=1, year=datetime.now().year, hour=23, minute=59)
    ): {
        "Logo": "logo_hub_blue.png",
        "Subtitle": "Happy new year!",
        "TitleText": "Happy new year!"
    }
}



# Hidden from regular signup
SOFT_LAUNCH_SERVICES = []

# Visibly disabled + excluded from synchronization
DISABLED_SERVICES = []
# Allow only these services to get connected
CONNECTION_SERVICES = []
# Services no longer available - will be removed across the site + excluded from sync.
WITHDRAWN_SERVICES = [
    "nikeplus"
    , "endomondo"
    , "motivato"
    , "pulsstory"
    , "runkeeper"
    , "setio"
    , "singletracker"
    , "sporttracks"
    , "trainasone"
    , "trainerroad"
    , "trainingpeaks"
    , "velohero"
]

# Where to put per-user sync logs
USER_SYNC_LOGS = "./"

# Set at startup
SITE_VER = "unknown"

# Cache lots of stuff to make local debugging faster
AGGRESSIVE_CACHE = True

# Diagnostics auth, None = no auth
DIAG_AUTH_LOGIN_SECRET = DIAG_AUTH_PASSWORD = None

SPORTTRACKS_OPENFIT_ENDPOINT = "https://api.sporttracks.mobi/api/v2"

EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
EMAIL_FILE_PATH = './sent_emails'

WORKER_INDEX = int(os.environ.get("TAPIRIIK_WORKER_INDEX", 0))

# Used for distributing outgoing calls across multiple interfaces

HTTP_SOURCE_ADDR = "0.0.0.0"

RABBITMQ_BROKER_URL = "amqp://guest@localhost//"

RABBITMQ_USER_QUEUE_STATS_URL = "http://guest:guest@localhost:15672/api/queues/%2F/tapiriik-users?lengths_age=3600&lengths_incr=60&msg_rates_age=3600&msg_rates_incr=60"

GARMIN_CONNECT_USER_WATCH_ACCOUNTS = {}

from .local_settings import *
