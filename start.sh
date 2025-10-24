#!/bin/bash

echo "🚀 Запуск приложения Family Health Center Bot..."

# Проверяем наличие DATABASE_URL
if [ -z "$DATABASE_URL" ]; then
    echo "❌ ОШИБКА: DATABASE_URL не установлена!"
    exit 1
fi

echo "✅ DATABASE_URL найдена: ${DATABASE_URL:0:20}..."

# Выполняем миграции
echo "📊 Выполнение миграций базы данных..."
python manage.py migrate --no-input --verbosity=2

if [ $? -eq 0 ]; then
    echo "✅ Миграции выполнены успешно"
else
    echo "❌ ОШИБКА при выполнении миграций!"
    exit 1
fi

# Загружаем начальные данные
echo "📋 Загрузка начальных данных..."
python manage.py load_initial_data

if [ $? -eq 0 ]; then
    echo "✅ Начальные данные загружены успешно"
else
    echo "⚠️  ПРЕДУПРЕЖДЕНИЕ: Ошибка при загрузке начальных данных"
fi

# Опционально: создание/сброс admin пользователя при старте (через переменные окружения)
# Установите AUTO_CREATE_ADMIN=true и (опционально) ADMIN_PASSWORD в Railway → Variables
if [ "${AUTO_CREATE_ADMIN:-false}" = "true" ]; then
    echo "👤 Создание/сброс admin пользователя..."

    if [ -z "$ADMIN_PASSWORD" ]; then
        echo "🔐 ADMIN_PASSWORD не задан — генерирую временный пароль..."
        ADMIN_PASSWORD=$(python - <<'PY'
import secrets, string
alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
print(''.join(secrets.choice(alphabet) for _ in range(20)))
PY
)
        echo "ℹ️ ВРЕМЕННЫЙ ПАРОЛЬ ДЛЯ admin: ${ADMIN_PASSWORD}"
    fi

    python manage.py reset_admin_password --password "$ADMIN_PASSWORD"
fi

# Собираем статические файлы
echo "📁 Сбор статических файлов..."
python manage.py collectstatic --noinput

if [ $? -eq 0 ]; then
    echo "✅ Статические файлы собраны успешно"
else
    echo "⚠️  ПРЕДУПРЕЖДЕНИЕ: Ошибка при сборе статических файлов"
fi

# Запускаем приложение
echo "🌐 Запуск веб-сервера..."
exec gunicorn smart_secretary.wsgi:application --bind 0.0.0.0:$PORT