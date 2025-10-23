#!/bin/bash
# Выполняем миграции перед запуском приложения
python manage.py migrate

# Загружаем начальные данные
python manage.py load_initial_data

# Запускаем приложение
exec gunicorn smart_secretary.wsgi:application
