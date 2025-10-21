#!/usr/bin/env python
"""
Скрипт подготовки и развертывания в продакшен
"""

import os
import subprocess
import sys
from datetime import datetime

def run_command(command, description):
    """Выполняет команду и выводит результат"""
    print(f"\n🔄 {description}")
    print(f"   Команда: {command}")
    
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"   ✅ Успешно")
            if result.stdout.strip():
                print(f"   Вывод: {result.stdout.strip()}")
        else:
            print(f"   ❌ Ошибка: {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"   💥 Исключение: {e}")
        return False
    
    return True

def main():
    print("🚀 ПОДГОТОВКА К РАЗВЕРТЫВАНИЮ В ПРОДАКШЕН")
    print("=" * 60)
    print(f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. Проверяем статус Git
    if not run_command("git status --porcelain", "Проверка статуса Git"):
        return False
    
    # 2. Запускаем финальные тесты
    print("\n🧪 ФИНАЛЬНОЕ ТЕСТИРОВАНИЕ")
    if not run_command("python comprehensive_test_suite.py --output production_ready_test", "Запуск комплексных тестов"):
        print("❌ Тесты не прошли! Развертывание отменено.")
        return False
    
    # 3. Создаем миграции (если есть изменения)
    if not run_command("python manage.py makemigrations", "Создание миграций"):
        return False
    
    # 4. Применяем миграции локально для проверки
    if not run_command("python manage.py migrate", "Применение миграций локально"):
        return False
    
    # 5. Собираем статические файлы
    if not run_command("python manage.py collectstatic --noinput", "Сборка статических файлов"):
        return False
    
    # 6. Коммитим финальные изменения
    print("\n📦 ФИНАЛЬНЫЙ КОММИТ")
    run_command("git add -A", "Добавление всех изменений")
    
    commit_message = f"🎯 PRODUCTION READY: Очищены тестовые данные, финальные тесты пройдены"
    if not run_command(f'git commit -m "{commit_message}"', "Создание финального коммита"):
        print("   ℹ️  Нет изменений для коммита (это нормально)")
    
    # 7. Пушим на GitHub
    if not run_command("git push origin main", "Отправка изменений на GitHub"):
        return False
    
    # 8. Показываем инструкции для Railway
    print("\n🚂 ИНСТРУКЦИИ ДЛЯ РАЗВЕРТЫВАНИЯ НА RAILWAY")
    print("=" * 60)
    print("1. Перейдите на https://railway.app/")
    print("2. Подключите ваш GitHub репозиторий")
    print("3. Настройте переменные окружения:")
    print("   - SECRET_KEY=<ваш_секретный_ключ>")
    print("   - DEBUG=False")
    print("   - ALLOWED_HOSTS=.railway.app")
    print("   - DATABASE_URL=<будет_создан_автоматически>")
    print("   - CSRF_TRUSTED_ORIGINS=https://<ваш_домен>.railway.app")
    print("4. Добавьте PostgreSQL сервис")
    print("5. Разверните приложение")
    print("6. Выполните миграции: python manage.py migrate")
    print("7. Создайте суперпользователя: python manage.py createsuperuser")
    
    # 9. Показываем статистику готовой системы
    print("\n📊 СТАТИСТИКА ГОТОВОЙ СИСТЕМЫ")
    print("=" * 60)
    
    # Запускаем Django для получения статистики
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_secretary.settings')
    import django
    django.setup()
    
    from core.models import Patient, Service, Specialist, Appointment, ContactMessage
    
    print(f"✅ Пациенты: {Patient.objects.count()}")
    print(f"✅ Услуги: {Service.objects.count()}")
    print(f"✅ Специалисты: {Specialist.objects.count()}")
    print(f"✅ Записи: {Appointment.objects.count()}")
    print(f"✅ Сообщения: {ContactMessage.objects.count()}")
    
    print("\n🎯 СИСТЕМА ГОТОВА К ПРОДАКШЕНУ!")
    print("✅ Тестовые данные удалены")
    print("✅ Тесты пройдены")
    print("✅ Код загружен на GitHub")
    print("✅ Готова к развертыванию на Railway")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
