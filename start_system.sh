#!/bin/bash

echo "🚀 ЗАПУСК СИСТЕМЫ SMART SECRETARY"
echo "=================================="

# Проверяем, что мы в правильной директории
if [ ! -f "manage.py" ]; then
    echo "❌ Ошибка: manage.py не найден. Запустите скрипт из корневой директории проекта."
    exit 1
fi

# Проверяем Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Ошибка: Python3 не установлен."
    exit 1
fi

# Проверяем зависимости
echo "📦 Проверка зависимостей..."
python3 -c "import django" 2>/dev/null || {
    echo "❌ Ошибка: Django не установлен. Устанавливаем зависимости..."
    pip3 install Django==4.2.7 APScheduler==3.10.4 openai==1.108.1 python-dotenv==1.0.0 requests==2.31.0 gunicorn==21.2.0 whitenoise==6.6.0 dj-database-url==2.1.0
}

# Применяем миграции
echo "🔄 Применение миграций..."
python3 manage.py migrate

# Собираем статические файлы
echo "📁 Сбор статических файлов..."
python3 manage.py collectstatic --noinput

# Проверяем систему
echo "🔍 Проверка системы..."
python3 manage.py check

# Запускаем сервер
echo "🌐 Запуск сервера на порту 8002..."
echo "=================================="
echo "✅ Система запущена!"
echo "📱 Админка: http://localhost:8002/admin/"
echo "👤 Логин: admin"
echo "🔑 Пароль: admin123"
echo "📊 Дашборд: http://localhost:8002/admin/dashboard/"
echo "🏠 Главная: http://localhost:8002/"
echo "=================================="
echo "Для остановки нажмите Ctrl+C"
echo ""

python3 manage.py runserver 0.0.0.0:8002
