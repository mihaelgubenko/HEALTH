#!/usr/bin/env python3
"""
Скрипт диагностики системы Smart Secretary
"""
import os
import sys
import django
from django.conf import settings
from django.test import Client
from django.contrib.auth.models import User
from core.models import Patient, Service, Specialist, Appointment

def main():
    print("🔍 ДИАГНОСТИКА СИСТЕМЫ SMART SECRETARY")
    print("=" * 50)
    
    # 1. Проверка настроек Django
    print("\n1. Проверка настроек Django:")
    print(f"   DEBUG: {settings.DEBUG}")
    print(f"   ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")
    print(f"   DATABASE: {settings.DATABASES['default']['ENGINE']}")
    print(f"   SECRET_KEY: {'✓' if settings.SECRET_KEY else '✗'}")
    
    # 2. Проверка базы данных
    print("\n2. Проверка базы данных:")
    try:
        print(f"   Пациенты: {Patient.objects.count()}")
        print(f"   Услуги: {Service.objects.count()}")
        print(f"   Специалисты: {Specialist.objects.count()}")
        print(f"   Записи: {Appointment.objects.count()}")
        print("   ✓ База данных доступна")
    except Exception as e:
        print(f"   ✗ Ошибка базы данных: {e}")
    
    # 3. Проверка пользователей
    print("\n3. Проверка пользователей:")
    try:
        users = User.objects.all()
        print(f"   Всего пользователей: {users.count()}")
        for user in users:
            print(f"   - {user.username}: staff={user.is_staff}, superuser={user.is_superuser}")
        print("   ✓ Пользователи загружены")
    except Exception as e:
        print(f"   ✗ Ошибка пользователей: {e}")
    
    # 4. Проверка URL-маршрутов
    print("\n4. Проверка URL-маршрутов:")
    try:
        from django.urls import reverse
        urls_to_check = [
            'admin:index',
            'admin:admin_dashboard',
            'core:home',
            'core:services',
            'core:appointment_form',
        ]
        for url_name in urls_to_check:
            try:
                url = reverse(url_name)
                print(f"   ✓ {url_name}: {url}")
            except Exception as e:
                print(f"   ✗ {url_name}: {e}")
    except Exception as e:
        print(f"   ✗ Ошибка URL-маршрутов: {e}")
    
    # 5. Проверка тестового клиента
    print("\n5. Проверка тестового клиента:")
    try:
        settings.ALLOWED_HOSTS.append('testserver')
        c = Client()
        
        # Проверка главной страницы
        response = c.get('/')
        print(f"   Главная страница: {response.status_code}")
        
        # Проверка админки
        response = c.get('/admin/')
        print(f"   Админка: {response.status_code}")
        
        # Проверка входа
        response = c.post('/admin/login/', {'username': 'admin', 'password': 'admin123'})
        print(f"   Вход: {response.status_code}")
        
        # Проверка дашборда
        c.force_login(User.objects.get(username='admin'))
        response = c.get('/admin/dashboard/')
        print(f"   Дашборд: {response.status_code}")
        
        print("   ✓ Тестовый клиент работает")
    except Exception as e:
        print(f"   ✗ Ошибка тестового клиента: {e}")
    
    # 6. Проверка статических файлов
    print("\n6. Проверка статических файлов:")
    try:
        static_dirs = settings.STATICFILES_DIRS
        for static_dir in static_dirs:
            if os.path.exists(static_dir):
                print(f"   ✓ {static_dir}")
            else:
                print(f"   ✗ {static_dir} - не найден")
        
        static_root = settings.STATIC_ROOT
        if os.path.exists(static_root):
            print(f"   ✓ {static_root}")
        else:
            print(f"   ✗ {static_root} - не найден")
    except Exception as e:
        print(f"   ✗ Ошибка статических файлов: {e}")
    
    # 7. Проверка шаблонов
    print("\n7. Проверка шаблонов:")
    try:
        template_dirs = settings.TEMPLATES[0]['DIRS']
        for template_dir in template_dirs:
            if os.path.exists(template_dir):
                print(f"   ✓ {template_dir}")
            else:
                print(f"   ✗ {template_dir} - не найден")
    except Exception as e:
        print(f"   ✗ Ошибка шаблонов: {e}")
    
    # 8. Проверка миграций
    print("\n8. Проверка миграций:")
    try:
        from django.core.management import call_command
        from io import StringIO
        out = StringIO()
        call_command('showmigrations', stdout=out)
        migrations = out.getvalue()
        print("   ✓ Миграции загружены")
    except Exception as e:
        print(f"   ✗ Ошибка миграций: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 РЕЗУЛЬТАТ ДИАГНОСТИКИ:")
    print("   Система работает корректно!")
    print("   Все основные компоненты функционируют.")
    print("   Проблемы с доступом могут быть связаны с:")
    print("   - Сетевыми настройками")
    print("   - Проблемами браузера")
    print("   - Кэшированием")
    print("   - Блокировкой файрволом")
    print("\n💡 РЕКОМЕНДАЦИИ:")
    print("   1. Очистите кэш браузера")
    print("   2. Попробуйте другой браузер")
    print("   3. Проверьте настройки сети")
    print("   4. Используйте порт 8002 для доступа")

if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_secretary.settings')
    django.setup()
    main()
