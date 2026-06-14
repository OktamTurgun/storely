#!/bin/bash
set -e

echo "Migration qilinmoqda..."
python manage.py migrate --noinput

echo "Static fayllar yig'ilmoqda..."
python manage.py collectstatic --noinput

echo "Django ishga tushmoqda..."
gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -