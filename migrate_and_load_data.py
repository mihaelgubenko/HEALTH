#!/usr/bin/env python
"""
Скрипт для выполнения миграций и загрузки тестовых данных
"""
import os
import sys
import django
from django.core.management import execute_from_command_line

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_secretary.settings')
django.setup()

def main():
    print("🚀 Начинаем выполнение миграций и загрузку данных...")
    
    # Выполняем миграции
    print("📊 Выполнение миграций...")
    try:
        execute_from_command_line(['manage.py', 'migrate', '--no-input'])
        print("✅ Миграции выполнены успешно")
    except Exception as e:
        print(f"❌ Ошибка при выполнении миграций: {e}")
        return False
    
    # Загружаем тестовые данные
    print("📋 Загрузка тестовых данных...")
    try:
        execute_from_command_line(['manage.py', 'load_initial_data'])
        print("✅ Тестовые данные загружены успешно")
    except Exception as e:
        print(f"⚠️  Предупреждение при загрузке данных: {e}")
    
    # Собираем статические файлы
    print("📁 Сбор статических файлов...")
    try:
        execute_from_command_line(['manage.py', 'collectstatic', '--noinput'])
        print("✅ Статические файлы собраны успешно")
    except Exception as e:
        print(f"⚠️  Предупреждение при сборе статических файлов: {e}")
    
    print("🎉 Все операции завершены успешно!")
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
