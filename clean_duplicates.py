#!/usr/bin/env python
"""
Скрипт очистки дубликатов в базе данных
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_secretary.settings')
django.setup()

from core.models import Patient, Service, Specialist
from django.db.models import Count

print('🧹 ОЧИСТКА ДУБЛИКАТОВ В БАЗЕ ДАННЫХ')
print('=' * 50)

# 1. Очистка дубликатов пациентов
print('\n👥 Очистка дубликатов пациентов:')
duplicates = Patient.objects.values('phone', 'name').annotate(count=Count('id')).filter(count__gt=1)

for duplicate in duplicates:
    phone = duplicate['phone']
    name = duplicate['name']
    count = duplicate['count']
    
    print(f'  Найдено {count} дубликатов для: {name} ({phone})')
    
    # Оставляем самого старого пациента, удаляем остальных
    patients = Patient.objects.filter(phone=phone, name=name).order_by('created_at')
    keep_patient = patients.first()
    
    # Переносим все записи на основного пациента
    for patient in patients[1:]:
        # Переносим записи
        patient.appointment_set.update(patient=keep_patient)
        print(f'    Перенесено записей: {patient.appointment_set.count()}')
        
        # Удаляем дубликат
        patient.delete()
        print(f'    Удален дубликат: {patient.name}')

# 2. Очистка дубликатов услуг
print('\n🏥 Очистка дубликатов услуг:')
service_duplicates = Service.objects.values('name').annotate(count=Count('id')).filter(count__gt=1)

for duplicate in service_duplicates:
    name = duplicate['name']
    count = duplicate['count']
    
    print(f'  Найдено {count} дубликатов услуги: {name}')
    
    # Оставляем самую старую услугу
    services = Service.objects.filter(name=name).order_by('created_at')
    keep_service = services.first()
    
    # Переносим все записи на основную услугу
    for service in services[1:]:
        # Переносим записи
        service.appointment_set.update(service=keep_service)
        print(f'    Перенесено записей: {service.appointment_set.count()}')
        
        # Удаляем дубликат
        service.delete()
        print(f'    Удалена дублирующая услуга: {service.name}')

# 3. Проверка специалистов
print('\n👨‍⚕️ Проверка дубликатов специалистов:')
specialist_duplicates = Specialist.objects.values('name').annotate(count=Count('id')).filter(count__gt=1)

for duplicate in specialist_duplicates:
    name = duplicate['name']
    count = duplicate['count']
    
    print(f'  Найдено {count} дубликатов специалиста: {name}')
    
    # Оставляем самого старого специалиста
    specialists = Specialist.objects.filter(name=name).order_by('created_at')
    keep_specialist = specialists.first()
    
    # Переносим все записи на основного специалиста
    for specialist in specialists[1:]:
        # Переносим записи
        specialist.appointment_set.update(specialist=keep_specialist)
        print(f'    Перенесено записей: {specialist.appointment_set.count()}')
        
        # Удаляем дубликат
        specialist.delete()
        print(f'    Удален дублирующий специалист: {specialist.name}')

# 4. Финальная статистика
print('\n📊 Финальная статистика:')
print(f'  Пациенты: {Patient.objects.count()}')
print(f'  Услуги: {Service.objects.count()}')
print(f'  Специалисты: {Specialist.objects.count()}')

print('\n✅ Очистка завершена!')
