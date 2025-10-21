#!/usr/bin/env python
"""
Очистка тестовых данных в продакшен базе данных Railway
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_secretary.settings')
django.setup()

from core.models import Patient, Service, Specialist, Appointment, ContactMessage
from django.db.models import Q

print('🧹 ОЧИСТКА ТЕСТОВЫХ ДАННЫХ В ПРОДАКШЕНЕ')
print('=' * 60)

# Расширенный список тестовых ключевых слов
TEST_KEYWORDS = [
    'тест', 'test', 'граничн', 'стресс', 'форма', 'debug', 'sample',
    'example', 'demo', 'временн', 'temp', 'tmp', 'fake', 'dummy',
    'нагрузочн', 'тестов', 'специальност', 'массаж', 'тестирован'
]

def is_test_data(text: str) -> bool:
    """Проверяет, является ли текст тестовым"""
    if not text:
        return False
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in TEST_KEYWORDS)

def cleanup_specialists():
    """Очистка тестовых специалистов"""
    print('\n👨‍⚕️ Очистка тестовых специалистов:')
    
    # Найти всех тестовых специалистов
    test_specialists = []
    for specialist in Specialist.objects.all():
        if (is_test_data(specialist.name) or 
            is_test_data(specialist.specialty) or
            specialist.name in ['Стресс Специалист', 'Тест Специалист', 'Тестовый Специалист', 
                               'Форма Специалист', 'Граничный Специалист']):
            test_specialists.append(specialist)
    
    print(f'  Найдено тестовых специалистов: {len(test_specialists)}')
    
    for specialist in test_specialists:
        print(f'    - Удаляем: {specialist.name} ({specialist.specialty})')
        
        # Удаляем связанные записи
        appointments = specialist.appointment_set.all()
        if appointments.exists():
            print(f'      Удаляем {appointments.count()} связанных записей')
            appointments.delete()
        
        # Удаляем специалиста
        specialist.delete()

def cleanup_services():
    """Очистка тестовых услуг"""
    print('\n🏥 Очистка тестовых услуг:')
    
    # Найти все тестовые услуги
    test_services = []
    for service in Service.objects.all():
        if (is_test_data(service.name) or
            service.name in ['Тест Услуга', 'Тестовая Услуга', 'Стресс Услуга', 
                           'Форма Услуга', 'Граничная Услуга']):
            test_services.append(service)
    
    print(f'  Найдено тестовых услуг: {len(test_services)}')
    
    for service in test_services:
        print(f'    - Удаляем: {service.name} ({service.price}{service.currency})')
        
        # Удаляем связанные записи
        appointments = service.appointment_set.all()
        if appointments.exists():
            print(f'      Удаляем {appointments.count()} связанных записей')
            appointments.delete()
        
        # Удаляем услугу
        service.delete()

def cleanup_patients():
    """Очистка тестовых пациентов"""
    print('\n👥 Очистка тестовых пациентов:')
    
    # Найти всех тестовых пациентов
    test_patients = []
    for patient in Patient.objects.all():
        if (is_test_data(patient.name) or 
            is_test_data(patient.phone) or
            patient.name.startswith('Стресс Пациент') or
            patient.name.startswith('Тест ') or
            'тест' in patient.name.lower()):
            test_patients.append(patient)
    
    print(f'  Найдено тестовых пациентов: {len(test_patients)}')
    
    for patient in test_patients:
        print(f'    - Удаляем: {patient.name} ({patient.phone})')
        
        # Удаляем связанные записи
        appointments = patient.appointment_set.all()
        if appointments.exists():
            print(f'      Удаляем {appointments.count()} связанных записей')
            appointments.delete()
        
        # Удаляем пациента
        patient.delete()

def cleanup_appointments():
    """Очистка оставшихся тестовых записей"""
    print('\n📅 Очистка оставшихся тестовых записей:')
    
    # Найти записи с тестовыми заметками или каналами
    test_appointments = Appointment.objects.filter(
        Q(notes__icontains='тест') | 
        Q(notes__icontains='test') |
        Q(channel__icontains='test')
    )
    
    print(f'  Найдено тестовых записей: {test_appointments.count()}')
    
    for appointment in test_appointments:
        print(f'    - Удаляем: {appointment.patient.name} -> {appointment.specialist.name}')
        appointment.delete()

def show_remaining_data():
    """Показать оставшиеся данные"""
    print('\n📊 ОСТАВШИЕСЯ ДАННЫЕ ПОСЛЕ ОЧИСТКИ:')
    
    print(f'\n  📈 Статистика:')
    print(f'    Пациенты: {Patient.objects.count()}')
    print(f'    Услуги: {Service.objects.count()}')
    print(f'    Специалисты: {Specialist.objects.count()}')
    print(f'    Записи: {Appointment.objects.count()}')
    print(f'    Сообщения: {ContactMessage.objects.count()}')
    
    print(f'\n  👨‍⚕️ Специалисты:')
    for specialist in Specialist.objects.all():
        print(f'    - {specialist.name} ({specialist.specialty})')
    
    print(f'\n  🏥 Услуги (первые 10):')
    for service in Service.objects.all()[:10]:
        print(f'    - {service.name} ({service.price}{service.currency})')
    
    print(f'\n  👥 Пациенты (последние 5):')
    for patient in Patient.objects.all().order_by('-created_at')[:5]:
        print(f'    - {patient.name} ({patient.phone})')

def main():
    """Основная функция очистки"""
    
    # Выполняем очистку по порядку
    cleanup_specialists()
    cleanup_services() 
    cleanup_patients()
    cleanup_appointments()
    
    # Показываем результат
    show_remaining_data()
    
    print('\n✅ ОЧИСТКА ЗАВЕРШЕНА!')
    print('🎯 Продакшен база данных очищена от тестовых данных!')

if __name__ == "__main__":
    main()
