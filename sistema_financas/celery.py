import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistema_financas.settings')

app = Celery('sistema_financas')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()