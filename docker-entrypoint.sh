#!/bin/sh
set -e

# Aplica migrations e coleta statics no primeiro comando do container.
# Comportamento padrao: gunicorn (web). Opcoes via SERVICE=web|worker|beat|migrate
python manage.py migrate --noinput
python manage.py collectstatic --noinput

case "${SERVICE:-web}" in
  web)
    exec gunicorn sistema_financas.wsgi:application \
      --bind 0.0.0.0:"${PORT:-8000}" \
      --workers "${WEB_CONCURRENCY:-3}" \
      --timeout 120
    ;;
  runserver)
    exec python manage.py runserver 0.0.0.0:"${PORT:-8000}" --noreload
    ;;
  worker)
    exec celery -A sistema_financas worker -l info
    ;;
  beat)
    exec celery -A sistema_financas beat -l info \
      --scheduler django_celery_beat.schedulers:DatabaseScheduler
    ;;
  migrate)
    echo "Migrations aplicadas com sucesso."
    ;;
  *)
    echo "SERVICE desconhecido: ${SERVICE}" >&2
    exit 1
    ;;
esac