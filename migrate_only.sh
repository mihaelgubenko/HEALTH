#!/bin/bash
echo "🚀 Выполнение миграций Django..."

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

echo "🎉 Миграции завершены!"
