#!/usr/bin/env bash
# Render: Build Command -> ./build.sh   |   Start Command -> gunicorn config.wsgi
set -o errexit
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate
