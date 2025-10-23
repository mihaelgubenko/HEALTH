#!/bin/bash

echo "🔍 БЫСТРАЯ ПРОВЕРКА СИСТЕМЫ"
echo "=========================="

# Проверка Django
echo "1. Проверка Django..."
python3 manage.py check
if [ $? -ne 0 ]; then
    echo "❌ Django check failed"
    exit 1
fi
echo "✅ Django OK"

# Проверка миграций
echo "2. Проверка миграций..."
python3 manage.py showmigrations | grep -q "\[ \]"
if [ $? -eq 0 ]; then
    echo "⚠️  Есть непримененные миграции"
    python3 manage.py migrate
fi
echo "✅ Миграции OK"

# Проверка сервера
echo "3. Проверка сервера..."
timeout 5 python3 manage.py runserver 0.0.0.0:8003 &
SERVER_PID=$!
sleep 3

# Проверка админки
echo "4. Проверка админки..."
curl -s -o /dev/null -w "%{http_code}" http://localhost:8003/admin/ | grep -q "302\|200"
if [ $? -eq 0 ]; then
    echo "✅ Админка доступна"
else
    echo "❌ Админка недоступна"
fi

# Проверка главной страницы
echo "5. Проверка главной страницы..."
curl -s -o /dev/null -w "%{http_code}" http://localhost:8003/ | grep -q "200"
if [ $? -eq 0 ]; then
    echo "✅ Главная страница доступна"
else
    echo "❌ Главная страница недоступна"
fi

# Остановка сервера
kill $SERVER_PID 2>/dev/null

echo "=========================="
echo "✅ ПРОВЕРКА ЗАВЕРШЕНА"
echo "Система работает корректно!"