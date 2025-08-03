#!/bin/sh

python manage.py makemigrations --no-input
python manage.py migrate --database('auth_db') --no-input
python manage.py collectstatic --no-input

gunicorn sisdm.wsgi:application --bind 0.0.0.0:8100