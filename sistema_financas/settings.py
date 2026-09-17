"""
Django settings for sistema_financas project.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# ===== Seguranca =====
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-fallback')
DEBUG = os.environ.get('DJANGO_DEBUG', 'True').lower() in ('true', '1', 'yes')
ALLOWED_HOSTS = [
    h.strip() for h in os.environ.get('DJANGO_ALLOWED_HOSTS', '127.0.0.1,localhost').split(',')
    if h.strip()
]
# Origens confiaveis para o CSRF (devem incluir o esquema https://)
# Ex.: https://financeiro.lucascoding.site,https://lucascoding.site
CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS', '').split(',')
    if o.strip()
]

# Aplica-se quando rodando atras do proxy HTTPS (Coolify/nginx/Caddy)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# ===== Application definition =====
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_celery_beat',
    'django_celery_results',
    # Apps do dominio
    'contas.apps.ContasConfig',
    'cartoes.apps.CartoesConfig',
    'dividas.apps.DividasConfig',
    'poupanca.apps.PoupancaConfig',
    'renda_fixa.apps.RendaFixaConfig',
    'renda_variavel.apps.RendaVariavelConfig',
    'cripto.apps.CriptoConfig',
    'contas_periodicas.apps.ContasPeriodicasConfig',
    'historico.apps.HistoricoConfig',
    'dashboard.apps.DashboardConfig',
    'assistente.apps.AssistenteConfig',
    'planejamento.apps.PlanejamentoConfig',
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

ROOT_URLCONF = 'sistema_financas.urls'

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
            ],
        },
    },
]

WSGI_APPLICATION = 'sistema_financas.wsgi.application'

# ===== Banco de dados =====
def _build_databases():
    engine = os.environ.get('DB_ENGINE', 'sqlite').strip().lower()
    if engine == 'mysql':
        return {
            'default': {
                'ENGINE': 'django.db.backends.mysql',
                'NAME': os.environ.get('DB_NAME', 'financas'),
                'USER': os.environ.get('DB_USER', ''),
                'PASSWORD': os.environ.get('DB_PASSWORD', ''),
                'HOST': os.environ.get('DB_HOST', '127.0.0.1'),
                'PORT': os.environ.get('DB_PORT', '3306'),
                'OPTIONS': {
                    'charset': 'utf8mb4',
                    'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
                },
            }
        }
    return {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

DATABASES = _build_databases()

# ===== Senha =====
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ===== Internacionalizacao =====
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# ===== Static =====
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# ===== Login / Autenticacao =====
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard:home'
LOGOUT_REDIRECT_URL = 'login'

# ===== Celery =====
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'memory://')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'django-db')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# ===== Config do snapshot de historico (em horas) =====
SNAPSHOT_INTERVALO_HORAS = 8

# ===== Assistente de IA (API Maritaca / OpenAI-compatível) =====
MARITACA_API_KEY = os.environ.get('MARITACA_API_KEY', '')
MARITACA_BASE_URL = os.environ.get('MARITACA_BASE_URL', 'https://chat.maritaca.ai/api')
MARITACA_MODEL = os.environ.get('MARITACA_MODEL', 'sabia-4')
MARITACA_MAX_TOKENS = int(os.environ.get('MARITACA_MAX_TOKENS', '2048'))
MARITACA_TIMEOUT = int(os.environ.get('MARITACA_TIMEOUT', '60'))