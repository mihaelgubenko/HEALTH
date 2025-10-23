#!/bin/bash
set -e  # Остановить выполнение при любой ошибке

echo "🚀 Запуск приложения Family Health Center Bot..."

# Проверяем наличие DATABASE_URL
if [ -z "$DATABASE_URL" ]; then
    echo "❌ ОШИБКА: DATABASE_URL не установлена!"
    exit 1
fi

echo "✅ DATABASE_URL найдена: ${DATABASE_URL:0:20}..."

# Выполняем миграции перед запуском приложения
echo "📊 Выполнение миграций базы данных..."
python manage.py migrate --no-input --verbosity=2

if [ $? -eq 0 ]; then
    echo "✅ Миграции выполнены успешно"
else
    echo "❌ ОШИБКА при выполнении миграций!"
    echo "Попытка выполнить миграции снова..."
    python manage.py migrate --no-input --verbosity=2
    if [ $? -ne 0 ]; then
        echo "❌ КРИТИЧЕСКАЯ ОШИБКА: Миграции не могут быть выполнены!"
        exit 1
    fi
fi

# Загружаем начальные данные
echo "📋 Загрузка начальных данных..."
python manage.py load_initial_data

if [ $? -eq 0 ]; then
    echo "✅ Начальные данные загружены успешно"
else
    echo "⚠️  ПРЕДУПРЕЖДЕНИЕ: Ошибка при загрузке начальных данных (продолжаем)"
fi

# Собираем статические файлы
echo "📁 Сбор статических файлов..."
python manage.py collectstatic --noinput

if [ $? -eq 0 ]; then
    echo "✅ Статические файлы собраны успешно"
else
    echo "⚠️  ПРЕДУПРЕЖДЕНИЕ: Ошибка при сборе статических файлов (продолжаем)"
fi

# Запускаем приложение
echo "🌐 Запуск веб-сервера..."
exec gunicorn smart_secretary.wsgi:application --bind 0.0.0.0:$PORT
