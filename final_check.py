#!/usr/bin/env python
"""
Финальная проверка основных компонентов
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_secretary.settings')
django.setup()

print('🔍 ФИНАЛЬНАЯ ПРОВЕРКА СИСТЕМЫ ВАЛИДАЦИИ')
print('=' * 60)

# 1. Валидация имен
from core.validators import NameValidator
print('\n✅ Валидация имен:')
test_names = [('Иван Петров', True), ('тест', False), ('admin', False)]
passed = 0
for name, expected in test_names:
    valid, _ = NameValidator.validate_name(name)
    status = '✅' if valid == expected else '❌'
    print(f'  {status} "{name}" -> {valid} (ожидалось {expected})')
    if valid == expected:
        passed += 1
print(f'  Результат: {passed}/{len(test_names)} тестов пройдено')

# 2. Валидация телефонов
from core.validators import PhoneValidator
print('\n✅ Валидация телефонов:')
test_phones = [('+972501234567', True), ('0501234567', True), ('123', False)]
passed = 0
for phone, expected in test_phones:
    valid, _, _ = PhoneValidator.validate_phone(phone)
    status = '✅' if valid == expected else '❌'
    print(f'  {status} "{phone}" -> {valid} (ожидалось {expected})')
    if valid == expected:
        passed += 1
print(f'  Результат: {passed}/{len(test_phones)} тестов пройдено')

# 3. Система бэкапа
print('\n✅ Система бэкапа:')
try:
    from deployment.backup_and_rollback import BackupAndRollback
    backup_system = BackupAndRollback()
    health = backup_system.health_check()
    all_good = all(health.values())
    print(f'  {"✅" if all_good else "❌"} Работоспособность: {all_good}')
    for component, status in health.items():
        print(f'    {component}: {"✅" if status else "❌"}')
except Exception as e:
    print(f'  ❌ Ошибка: {e}')

# 4. Комплексная валидация
print('\n✅ Комплексная валидация:')
try:
    from core.validators import ValidationManager
    validator = ValidationManager()
    
    # Тест корректных данных
    result = validator.validate_appointment_data(
        name="Иван Петров",  # Используем корректное имя
        phone="+972501234567",
        service_name="Массаж",  # Используем существующую услугу
        specialist_name="Авраам",  # Используем существующего специалиста
        date="2025-12-31",
        time_str="15:00"
    )
    
    print(f'  {"✅" if result["is_valid"] else "❌"} Валидация корректных данных: {result["is_valid"]}')
    if not result["is_valid"]:
        print(f'    Ошибки: {result["errors"]}')
        
except Exception as e:
    print(f'  ❌ Ошибка валидации: {e}')

# 5. Проверка моделей
print('\n✅ Модели Django:')
try:
    from core.models import Patient, Specialist, Service, Appointment
    
    patients_count = Patient.objects.count()
    specialists_count = Specialist.objects.count()
    services_count = Service.objects.count()
    appointments_count = Appointment.objects.count()
    
    print(f'  ✅ Пациенты: {patients_count}')
    print(f'  ✅ Специалисты: {specialists_count}')
    print(f'  ✅ Услуги: {services_count}')
    print(f'  ✅ Записи: {appointments_count}')
    
except Exception as e:
    print(f'  ❌ Ошибка моделей: {e}')

print('\n' + '=' * 60)
print('🎯 ФИНАЛЬНАЯ ПРОВЕРКА ЗАВЕРШЕНА!')
print('=' * 60)
