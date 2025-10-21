#!/usr/bin/env python
"""
Очистка тестовых данных перед развертыванием в продакшен
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_secretary.settings')
django.setup()

from core.models import Patient, Service, Specialist, Appointment, ContactMessage
from django.db.models import Q

print('🧹 ОЧИСТКА ТЕСТОВЫХ ДАННЫХ ПЕРЕД ПРОДАКШЕНОМ')
print('=' * 60)

# Список тестовых ключевых слов для поиска
TEST_KEYWORDS = [
    'тест', 'test', 'граничн', 'стресс', 'форма', 'debug', 'sample',
    'example', 'demo', 'временн', 'temp', 'tmp', 'fake', 'dummy'
]

def is_test_data(name: str) -> bool:
    """Проверяет, является ли запись тестовой"""
    name_lower = name.lower()
    return any(keyword in name_lower for keyword in TEST_KEYWORDS)

# 1. Очистка тестовых пациентов
print('\n👥 Очистка тестовых пациентов:')
test_patients = []
for patient in Patient.objects.all():
    if is_test_data(patient.name) or is_test_data(patient.phone):
        test_patients.append(patient)

print(f'  Найдено тестовых пациентов: {len(test_patients)}')
for patient in test_patients:
    print(f'    - {patient.name} ({patient.phone})')
    # Сначала удаляем связанные записи
    appointments_count = patient.appointment_set.count()
    if appointments_count > 0:
        print(f'      Удаляем {appointments_count} связанных записей')
        patient.appointment_set.all().delete()
    patient.delete()

# 2. Очистка тестовых услуг
print('\n🏥 Очистка тестовых услуг:')
test_services = []
for service in Service.objects.all():
    if is_test_data(service.name):
        test_services.append(service)

print(f'  Найдено тестовых услуг: {len(test_services)}')
for service in test_services:
    print(f'    - {service.name} ({service.price}{service.currency})')
    # Сначала удаляем связанные записи
    appointments_count = service.appointment_set.count()
    if appointments_count > 0:
        print(f'      Удаляем {appointments_count} связанных записей')
        service.appointment_set.all().delete()
    service.delete()

# 3. Очистка тестовых специалистов
print('\n👨‍⚕️ Очистка тестовых специалистов:')
test_specialists = []
for specialist in Specialist.objects.all():
    if is_test_data(specialist.name) or is_test_data(specialist.specialty):
        test_specialists.append(specialist)

print(f'  Найдено тестовых специалистов: {len(test_specialists)}')
for specialist in test_specialists:
    print(f'    - {specialist.name} ({specialist.specialty})')
    # Сначала удаляем связанные записи
    appointments_count = specialist.appointment_set.count()
    if appointments_count > 0:
        print(f'      Удаляем {appointments_count} связанных записей')
        specialist.appointment_set.all().delete()
    specialist.delete()

# 4. Очистка тестовых записей (оставшихся)
print('\n📅 Очистка оставшихся тестовых записей:')
test_appointments = []
for appointment in Appointment.objects.all():
    # Проверяем по заметкам или каналу
    if (appointment.notes and is_test_data(appointment.notes)) or \
       (appointment.channel and is_test_data(appointment.channel)):
        test_appointments.append(appointment)

print(f'  Найдено тестовых записей: {len(test_appointments)}')
for appointment in test_appointments:
    print(f'    - {appointment.patient.name} -> {appointment.specialist.name} ({appointment.start_time})')
    appointment.delete()

# 5. Очистка тестовых сообщений
print('\n📧 Очистка тестовых сообщений:')
test_messages = []
for message in ContactMessage.objects.all():
    if is_test_data(message.name) or is_test_data(message.message):
        test_messages.append(message)

print(f'  Найдено тестовых сообщений: {len(test_messages)}')
for message in test_messages:
    print(f'    - {message.name} ({message.phone})')
    message.delete()

# 6. Финальная статистика
print('\n📊 ФИНАЛЬНАЯ СТАТИСТИКА ПОСЛЕ ОЧИСТКИ:')
print(f'  Пациенты: {Patient.objects.count()}')
print(f'  Услуги: {Service.objects.count()}')
print(f'  Специалисты: {Specialist.objects.count()}')
print(f'  Записи: {Appointment.objects.count()}')
print(f'  Сообщения: {ContactMessage.objects.count()}')

# 7. Показываем оставшиеся данные для проверки
print('\n🔍 ОСТАВШИЕСЯ ДАННЫЕ (для проверки):')

print('\n  Услуги:')
for service in Service.objects.all()[:10]:
    print(f'    - {service.name} ({service.price}{service.currency})')

print('\n  Специалисты:')
for specialist in Specialist.objects.all()[:10]:
    print(f'    - {specialist.name} ({specialist.specialty})')

print('\n  Пациенты (последние 5):')
for patient in Patient.objects.all().order_by('-created_at')[:5]:
    print(f'    - {patient.name} ({patient.phone})')

print('\n✅ ОЧИСТКА ЗАВЕРШЕНА!')
print('🎯 Система готова к продакшену!')
