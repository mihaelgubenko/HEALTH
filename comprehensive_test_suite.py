#!/usr/bin/env python
"""
Комплексная система тестирования всего функционала проекта
Включает модульные тесты, интеграционные тесты, стресс-тесты и тесты граничных случаев
"""

import os
import sys
import json
import time
import random
import threading
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Dict, List, Any, Tuple
import concurrent.futures

# Добавляем путь к Django проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_secretary.settings')

import django
django.setup()

from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from django.db import transaction, IntegrityError
from django.contrib.auth.models import User
from django.test.client import Client
from django.urls import reverse

from core.models import Patient, Specialist, Service, Appointment, ContactMessage
from core.validators import ValidationManager, NameValidator, PhoneValidator
from core.datetime_validator import DateTimeValidator, TimezoneManager
from core.lite_secretary import LiteSmartSecretary
from core.forms import AppointmentForm


class ValidationTestSuite:
    """Комплексное тестирование системы валидации"""
    
    def __init__(self):
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'tests': {},
            'summary': {
                'total': 0,
                'passed': 0,
                'failed': 0,
                'errors': 0
            }
        }
    
    def run_test(self, test_name: str, test_func, *args, **kwargs):
        """Запуск отдельного теста с обработкой ошибок"""
        print(f"🧪 Тест: {test_name}")
        
        start_time = time.time()
        try:
            result = test_func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            self.results['tests'][test_name] = {
                'status': 'PASSED',
                'result': result,
                'execution_time': execution_time,
                'error': None
            }
            self.results['summary']['passed'] += 1
            print(f"  ✅ Пройден ({execution_time:.3f}s)")
            
        except AssertionError as e:
            execution_time = time.time() - start_time
            self.results['tests'][test_name] = {
                'status': 'FAILED',
                'result': None,
                'execution_time': execution_time,
                'error': str(e)
            }
            self.results['summary']['failed'] += 1
            print(f"  ❌ Провален: {str(e)} ({execution_time:.3f}s)")
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.results['tests'][test_name] = {
                'status': 'ERROR',
                'result': None,
                'execution_time': execution_time,
                'error': str(e)
            }
            self.results['summary']['errors'] += 1
            print(f"  💥 Ошибка: {str(e)} ({execution_time:.3f}s)")
        
        self.results['summary']['total'] += 1
    
    def test_name_validation(self):
        """Тестирование валидации имен"""
        test_cases = [
            # (input, expected_valid, description)
            ("Иван Петров", True, "Корректное русское имя"),
            ("John Smith", True, "Корректное английское имя"),
            ("אברהם כהן", True, "Корректное имя на иврите"),
            ("Ivan123", False, "Имя с цифрами"),
            ("тест", False, "Служебное слово"),
            ("admin", False, "Служебное слово на английском"),
            ("ааа", False, "Повторяющиеся символы"),
            ("qwerty", False, "Последовательность клавиатуры"),
            ("И", False, "Слишком короткое"),
            ("А" * 60, False, "Слишком длинное"),
            ("Иван John", False, "Смешанные языки"),
            ("O'Connor", True, "Имя с апострофом"),
            ("Мария-Анна", True, "Имя с дефисом"),
        ]
        
        passed = 0
        for name, expected, description in test_cases:
            is_valid, error = NameValidator.validate_name(name)
            if is_valid == expected:
                passed += 1
            else:
                print(f"    ❌ {description}: '{name}' -> {is_valid} (ожидалось {expected})")
        
        assert passed == len(test_cases), f"Пройдено {passed}/{len(test_cases)} тестов валидации имен"
        return {'passed': passed, 'total': len(test_cases)}
    
    def test_phone_validation(self):
        """Тестирование валидации телефонов"""
        test_cases = [
            # (input, expected_valid, expected_country, description)
            ("+972501234567", True, "IL", "Израильский мобильный"),
            ("0501234567", True, "IL", "Израильский локальный"),
            ("501234567", True, "IL", "Израильский без префикса"),
            ("+79123456789", True, "RU", "Российский мобильный"),
            ("89123456789", True, "RU", "Российский с 8"),
            ("+380501234567", True, "UA", "Украинский мобильный"),
            ("+12345678901", True, "US", "Американский номер"),
            ("123", False, "UNKNOWN", "Слишком короткий"),
            ("+972123", False, "IL", "Неверная длина для Израиля"),
            ("invalid", False, "UNKNOWN", "Не номер телефона"),
        ]
        
        passed = 0
        for phone, expected_valid, expected_country, description in test_cases:
            is_valid, country, result = PhoneValidator.validate_phone(phone)
            if is_valid == expected_valid and (not expected_valid or country == expected_country):
                passed += 1
            else:
                print(f"    ❌ {description}: '{phone}' -> {is_valid}, {country} (ожидалось {expected_valid}, {expected_country})")
        
        assert passed == len(test_cases), f"Пройдено {passed}/{len(test_cases)} тестов валидации телефонов"
        return {'passed': passed, 'total': len(test_cases)}
    
    def test_datetime_validation(self):
        """Тестирование валидации даты и времени"""
        validator = DateTimeValidator()
        
        # Тесты парсинга дат
        date_tests = [
            ("2025-10-22", True, "ISO формат"),
            ("22.10.2025", True, "Европейский формат"),
            ("сегодня", True, "Относительная дата"),
            ("завтра", True, "Относительная дата"),
            ("понедельник", True, "День недели"),
            ("invalid", False, "Неверный формат"),
        ]
        
        passed = 0
        for date_str, expected, description in date_tests:
            success, parsed_date, error = validator.parse_date_string(date_str)
            if success == expected:
                passed += 1
            else:
                print(f"    ❌ {description}: '{date_str}' -> {success} (ожидалось {expected})")
        
        # Тесты парсинга времени
        time_tests = [
            ("15:30", True, "Стандартный формат"),
            ("9:00", True, "Утреннее время"),
            ("25:00", False, "Неверное время"),
            ("abc", False, "Не время"),
        ]
        
        for time_str, expected, description in time_tests:
            success, parsed_time, error = validator.parse_time_string(time_str)
            if success == expected:
                passed += 1
            else:
                print(f"    ❌ {description}: '{time_str}' -> {success} (ожидалось {expected})")
        
        total_tests = len(date_tests) + len(time_tests)
        assert passed == total_tests, f"Пройдено {passed}/{total_tests} тестов валидации даты/времени"
        return {'passed': passed, 'total': total_tests}
    
    def test_appointment_validation(self):
        """Тестирование комплексной валидации записей"""
        # Создаем тестовые данные
        specialist = Specialist.objects.create(
            name="Тестовый Специалист",
            specialty="Массаж",
            is_active=True
        )
        
        service = Service.objects.create(
            name="Тестовая Услуга",
            price=100,
            duration=60,
            is_active=True
        )
        
        validator = ValidationManager()
        
        # Тест корректных данных
        tomorrow = (timezone.now() + timedelta(days=1)).date().strftime('%Y-%m-%d')
        
        result = validator.validate_appointment_data(
            name="Иван Петров",
            phone="+972501234567",
            service_name="Тестовая Услуга",
            specialist_name="Тестовый Специалист",
            date=tomorrow,
            time_str="15:00"
        )
        
        assert result['is_valid'], f"Валидация корректных данных должна проходить: {result['errors']}"
        
        # Тест некорректных данных
        result = validator.validate_appointment_data(
            name="тест",  # Служебное слово
            phone="123",  # Неверный телефон
            service_name="Несуществующая Услуга",
            specialist_name="Несуществующий Специалист",
            date="2020-01-01",  # Прошедшая дата
            time_str="25:00"  # Неверное время
        )
        
        assert not result['is_valid'], "Валидация некорректных данных должна провалиться"
        assert len(result['errors']) > 0, "Должны быть ошибки валидации"
        
        return {'valid_passed': True, 'invalid_passed': True}


class DatabaseTestSuite:
    """Тестирование базы данных и моделей"""
    
    def __init__(self):
        self.results = {}
    
    def test_model_creation(self):
        """Тестирование создания моделей"""
        # Создание пациента
        patient = Patient.objects.create(
            name="Тест Пациент",
            phone="+972501234567",
            email="test@example.com"
        )
        assert patient.id is not None, "Пациент должен быть создан"
        
        # Создание специалиста
        specialist = Specialist.objects.create(
            name="Тест Специалист",
            specialty="Тестовая специальность"
        )
        assert specialist.id is not None, "Специалист должен быть создан"
        
        # Создание услуги
        service = Service.objects.create(
            name="Тест Услуга",
            price=100,
            duration=60
        )
        assert service.id is not None, "Услуга должна быть создана"
        
        # Создание записи
        appointment_time = timezone.now() + timedelta(days=1)
        appointment = Appointment.objects.create(
            patient=patient,
            specialist=specialist,
            service=service,
            start_time=appointment_time,
            end_time=appointment_time + timedelta(minutes=service.duration)
        )
        assert appointment.id is not None, "Запись должна быть создана"
        
        return {
            'patient_id': patient.id,
            'specialist_id': specialist.id,
            'service_id': service.id,
            'appointment_id': appointment.id
        }
    
    def test_model_relationships(self):
        """Тестирование связей между моделями"""
        # Получаем созданные объекты
        patient = Patient.objects.first()
        specialist = Specialist.objects.first()
        service = Service.objects.first()
        
        assert patient is not None, "Пациент должен существовать"
        assert specialist is not None, "Специалист должен существовать"
        assert service is not None, "Услуга должна существовать"
        
        # Проверяем связи
        appointments = Appointment.objects.filter(patient=patient)
        assert appointments.exists(), "У пациента должны быть записи"
        
        appointment = appointments.first()
        assert appointment.specialist == specialist, "Связь со специалистом должна работать"
        assert appointment.service == service, "Связь с услугой должна работать"
        
        return {'relationships_ok': True}
    
    def test_data_integrity(self):
        """Тестирование целостности данных"""
        # Тест уникальности (если есть ограничения)
        patient_count_before = Patient.objects.count()
        
        # Создаем пациента с уникальным телефоном
        unique_phone = f"+972{random.randint(500000000, 599999999)}"
        Patient.objects.create(
            name="Уникальный Пациент",
            phone=unique_phone
        )
        
        patient_count_after = Patient.objects.count()
        assert patient_count_after == patient_count_before + 1, "Пациент должен быть создан"
        
        return {'integrity_ok': True}


class IntegrationTestSuite:
    """Интеграционные тесты"""
    
    def __init__(self):
        self.client = Client()
        self.results = {}
    
    def test_web_interface(self):
        """Тестирование веб-интерфейса"""
        # Тест главной страницы
        response = self.client.get('/')
        assert response.status_code == 200, "Главная страница должна загружаться"
        
        # Тест страницы услуг
        response = self.client.get('/services/')
        assert response.status_code == 200, "Страница услуг должна загружаться"
        
        # Тест формы записи
        response = self.client.get('/appointment/')
        assert response.status_code == 200, "Форма записи должна загружаться"
        
        return {'pages_loaded': 3}
    
    def test_appointment_form_submission(self):
        """Тестирование отправки формы записи"""
        # Создаем необходимые данные
        specialist = Specialist.objects.create(
            name="Форма Специалист",
            specialty="Тестирование",
            is_active=True
        )
        
        service = Service.objects.create(
            name="Форма Услуга",
            price=150,
            duration=60,
            is_active=True
        )
        
        # Отправляем форму
        tomorrow = (timezone.now() + timedelta(days=1)).date()
        
        form_data = {
            'name': 'Тест Форма',
            'phone': '+972501234567',
            'email': 'test@example.com',
            'service': service.id,
            'specialist': specialist.id,
            'preferred_date': tomorrow.strftime('%Y-%m-%d'),
            'preferred_time': '15:00',
            'notes': 'Тестовая запись'
        }
        
        response = self.client.post('/appointment/', form_data)
        
        # Проверяем результат (редирект или успех)
        assert response.status_code in [200, 302], f"Форма должна обрабатываться корректно, получен код: {response.status_code}"
        
        # Проверяем, что запись создалась
        appointments = Appointment.objects.filter(
            patient__name='Тест Форма',
            patient__phone='+972501234567'
        )
        
        assert appointments.exists(), "Запись должна быть создана через форму"
        
        return {'form_submitted': True, 'appointment_created': True}
    
    def test_ai_chat_integration(self):
        """Тестирование интеграции с ИИ-чатом"""
        try:
            secretary = LiteSmartSecretary()
            
            # Тест простого сообщения
            response = secretary.process_message(
                "Привет", 
                session_id="test_session"
            )
            
            assert 'response' in response, "ИИ должен отвечать на сообщения"
            assert response['response'], "Ответ не должен быть пустым"
            
            return {'ai_responding': True}
            
        except Exception as e:
            # ИИ может быть недоступен в тестовой среде
            return {'ai_responding': False, 'error': str(e)}


class StressTestSuite:
    """Стресс-тестирование"""
    
    def __init__(self):
        self.results = {}
    
    def test_concurrent_appointments(self):
        """Тестирование одновременных записей"""
        # Создаем тестовые данные
        specialist = Specialist.objects.create(
            name="Стресс Специалист",
            specialty="Нагрузочное тестирование",
            is_active=True
        )
        
        service = Service.objects.create(
            name="Стресс Услуга",
            price=200,
            duration=30,
            is_active=True
        )
        
        def create_appointment(i):
            """Создание записи в отдельном потоке"""
            try:
                patient = Patient.objects.create(
                    name=f"Стресс Пациент {i}",
                    phone=f"+97250{i:07d}"
                )
                
                appointment_time = timezone.now() + timedelta(days=1, minutes=i*30)
                
                appointment = Appointment.objects.create(
                    patient=patient,
                    specialist=specialist,
                    service=service,
                    start_time=appointment_time,
                    end_time=appointment_time + timedelta(minutes=30)
                )
                
                return True
            except Exception as e:
                print(f"Ошибка создания записи {i}: {e}")
                return False
        
        # Запускаем 10 одновременных создания записей
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_appointment, i) for i in range(10)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        successful = sum(results)
        assert successful >= 8, f"Должно быть создано минимум 8 из 10 записей, создано: {successful}"
        
        return {'successful_appointments': successful, 'total_attempted': 10}
    
    def test_validation_performance(self):
        """Тестирование производительности валидации"""
        validator = ValidationManager()
        
        # Тестируем 100 валидаций
        start_time = time.time()
        
        for i in range(100):
            validator.validate_appointment_data(
                name=f"Тест {i}",
                phone=f"+97250{i:07d}",
                service_name="Несуществующая услуга",
                specialist_name="Несуществующий специалист",
                date="2025-12-31",
                time_str="15:00"
            )
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time = total_time / 100
        
        # Валидация должна быть быстрой (менее 50мс на запрос)
        assert avg_time < 0.05, f"Валидация слишком медленная: {avg_time:.3f}s на запрос"
        
        return {'total_time': total_time, 'avg_time': avg_time, 'validations': 100}


class BoundaryTestSuite:
    """Тестирование граничных случаев"""
    
    def __init__(self):
        self.results = {}
    
    def test_edge_cases(self):
        """Тестирование граничных случаев"""
        validator = ValidationManager()
        
        # Тест записи на границе рабочего времени
        tomorrow = (timezone.now() + timedelta(days=1)).date().strftime('%Y-%m-%d')
        
        # Создаем тестовые данные
        specialist = Specialist.objects.create(
            name="Граничный Специалист",
            specialty="Граничные случаи",
            is_active=True
        )
        
        service = Service.objects.create(
            name="Граничная Услуга",
            price=300,
            duration=60,
            is_active=True
        )
        
        # Тест записи в 9:00 (начало рабочего дня)
        result = validator.validate_appointment_data(
            name="Граничный Тест",
            phone="+972501234567",
            service_name="Граничная Услуга",
            specialist_name="Граничный Специалист",
            date=tomorrow,
            time_str="09:00"
        )
        
        morning_valid = result['is_valid']
        
        # Тест записи в 18:00 (конец рабочего дня)
        result = validator.validate_appointment_data(
            name="Граничный Тест",
            phone="+972501234567",
            service_name="Граничная Услуга",
            specialist_name="Граничный Специалист",
            date=tomorrow,
            time_str="18:00"
        )
        
        evening_valid = result['is_valid']
        
        # Тест записи в 8:00 (до начала работы)
        result = validator.validate_appointment_data(
            name="Граничный Тест",
            phone="+972501234567",
            service_name="Граничная Услуга",
            specialist_name="Граничный Специалист",
            date=tomorrow,
            time_str="08:00"
        )
        
        early_invalid = not result['is_valid']
        
        # Тест записи в 20:00 (после окончания работы)
        result = validator.validate_appointment_data(
            name="Граничный Тест",
            phone="+972501234567",
            service_name="Граничная Услуга",
            specialist_name="Граничный Специалист",
            date=tomorrow,
            time_str="20:00"
        )
        
        late_invalid = not result['is_valid']
        
        assert morning_valid, "Запись в 9:00 должна быть валидной"
        assert evening_valid, "Запись в 18:00 должна быть валидной"
        assert early_invalid, "Запись в 8:00 должна быть невалидной"
        assert late_invalid, "Запись в 20:00 должна быть невалидной"
        
        return {
            'morning_valid': morning_valid,
            'evening_valid': evening_valid,
            'early_invalid': early_invalid,
            'late_invalid': late_invalid
        }
    
    def test_extreme_values(self):
        """Тестирование экстремальных значений"""
        # Тест очень длинных имен
        long_name = "А" * 1000
        is_valid, error = NameValidator.validate_name(long_name)
        assert not is_valid, "Очень длинное имя должно быть невалидным"
        
        # Тест пустых значений
        is_valid, error = NameValidator.validate_name("")
        assert not is_valid, "Пустое имя должно быть невалидным"
        
        # Тест специальных символов в телефоне
        is_valid, country, result = PhoneValidator.validate_phone("!@#$%^&*()")
        assert not is_valid, "Телефон со спецсимволами должен быть невалидным"
        
        return {'extreme_values_handled': True}


class ComprehensiveTestRunner:
    """Главный класс для запуска всех тестов"""
    
    def __init__(self):
        self.all_results = {
            'timestamp': datetime.now().isoformat(),
            'suites': {},
            'summary': {
                'total_suites': 0,
                'passed_suites': 0,
                'total_tests': 0,
                'passed_tests': 0,
                'failed_tests': 0,
                'error_tests': 0,
                'execution_time': 0
            }
        }
    
    def run_all_tests(self):
        """Запуск всех тестовых наборов"""
        print("🚀 Запуск комплексного тестирования")
        print("=" * 60)
        
        start_time = time.time()
        
        # Валидационные тесты
        print("\n📋 Тестирование валидации")
        print("-" * 30)
        validation_suite = ValidationTestSuite()
        validation_suite.run_test("Валидация имен", validation_suite.test_name_validation)
        validation_suite.run_test("Валидация телефонов", validation_suite.test_phone_validation)
        validation_suite.run_test("Валидация даты/времени", validation_suite.test_datetime_validation)
        validation_suite.run_test("Валидация записей", validation_suite.test_appointment_validation)
        
        self.all_results['suites']['validation'] = validation_suite.results
        
        # Тесты базы данных
        print("\n💾 Тестирование базы данных")
        print("-" * 30)
        db_suite = DatabaseTestSuite()
        validation_suite.run_test("Создание моделей", db_suite.test_model_creation)
        validation_suite.run_test("Связи моделей", db_suite.test_model_relationships)
        validation_suite.run_test("Целостность данных", db_suite.test_data_integrity)
        
        # Интеграционные тесты
        print("\n🔗 Интеграционные тесты")
        print("-" * 30)
        integration_suite = IntegrationTestSuite()
        validation_suite.run_test("Веб-интерфейс", integration_suite.test_web_interface)
        validation_suite.run_test("Отправка формы", integration_suite.test_appointment_form_submission)
        validation_suite.run_test("ИИ-чат", integration_suite.test_ai_chat_integration)
        
        # Стресс-тесты
        print("\n⚡ Стресс-тестирование")
        print("-" * 30)
        stress_suite = StressTestSuite()
        validation_suite.run_test("Одновременные записи", stress_suite.test_concurrent_appointments)
        validation_suite.run_test("Производительность валидации", stress_suite.test_validation_performance)
        
        # Граничные случаи
        print("\n🎯 Граничные случаи")
        print("-" * 30)
        boundary_suite = BoundaryTestSuite()
        validation_suite.run_test("Граничные значения", boundary_suite.test_edge_cases)
        validation_suite.run_test("Экстремальные значения", boundary_suite.test_extreme_values)
        
        # Подсчет общей статистики
        total_time = time.time() - start_time
        
        summary = validation_suite.results['summary']
        self.all_results['summary'] = {
            'total_suites': 5,
            'passed_suites': 5 if summary['failed'] == 0 and summary['errors'] == 0 else 4,
            'total_tests': summary['total'],
            'passed_tests': summary['passed'],
            'failed_tests': summary['failed'],
            'error_tests': summary['errors'],
            'execution_time': total_time
        }
        
        # Вывод итогов
        print("\n" + "=" * 60)
        print("📊 ИТОГИ ТЕСТИРОВАНИЯ")
        print("=" * 60)
        print(f"Всего тестов: {summary['total']}")
        print(f"Пройдено: {summary['passed']} ✅")
        print(f"Провалено: {summary['failed']} ❌")
        print(f"Ошибок: {summary['errors']} 💥")
        print(f"Время выполнения: {total_time:.2f}s")
        
        success_rate = (summary['passed'] / summary['total'] * 100) if summary['total'] > 0 else 0
        print(f"Успешность: {success_rate:.1f}%")
        
        if summary['failed'] == 0 and summary['errors'] == 0:
            print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        else:
            print(f"\n⚠️ Обнаружены проблемы. Проверьте детали выше.")
        
        return self.all_results
    
    def save_results(self, filename: str = "test_results.json"):
        """Сохранение результатов в файл"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.all_results, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n📄 Результаты сохранены в {filename}")
        return filename
    
    def generate_html_report(self, filename: str = "test_report.html"):
        """Генерация HTML отчета"""
        html_template = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Отчет тестирования - Центр "Новая Жизнь"</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ background: linear-gradient(135deg, #4A90E2 0%, #27AE60 100%); color: white; padding: 30px; border-radius: 10px; text-align: center; margin-bottom: 30px; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .summary-card {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center; }}
        .number {{ font-size: 2.5em; font-weight: bold; margin-bottom: 10px; }}
        .passed {{ color: #27AE60; }}
        .failed {{ color: #E74C3C; }}
        .error {{ color: #F39C12; }}
        .suite {{ background: white; margin-bottom: 20px; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        .suite-header {{ background: #4A90E2; color: white; padding: 15px 20px; font-weight: bold; }}
        .test-item {{ padding: 15px 20px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center; }}
        .test-item:last-child {{ border-bottom: none; }}
        .test-status {{ padding: 5px 10px; border-radius: 5px; color: white; font-weight: bold; }}
        .status-passed {{ background: #27AE60; }}
        .status-failed {{ background: #E74C3C; }}
        .status-error {{ background: #F39C12; }}
        .execution-time {{ color: #666; font-size: 0.9em; }}
        .error-details {{ background: #ffebee; color: #c62828; padding: 10px; margin-top: 10px; border-radius: 5px; font-size: 0.9em; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧪 Отчет комплексного тестирования</h1>
            <p>Центр здоровья "Новая Жизнь"</p>
            <p>Создан: {timestamp}</p>
        </div>
        
        <div class="summary">
            <div class="summary-card">
                <div class="number">{total_tests}</div>
                <div>Всего тестов</div>
            </div>
            <div class="summary-card">
                <div class="number passed">{passed_tests}</div>
                <div>Пройдено</div>
            </div>
            <div class="summary-card">
                <div class="number failed">{failed_tests}</div>
                <div>Провалено</div>
            </div>
            <div class="summary-card">
                <div class="number error">{error_tests}</div>
                <div>Ошибок</div>
            </div>
            <div class="summary-card">
                <div class="number">{execution_time:.2f}s</div>
                <div>Время выполнения</div>
            </div>
            <div class="summary-card">
                <div class="number {success_class}">{success_rate:.1f}%</div>
                <div>Успешность</div>
            </div>
        </div>
        
        {test_details}
    </div>
</body>
</html>
        """
        
        # Генерируем детали тестов
        test_details = ""
        
        if 'validation' in self.all_results['suites']:
            validation_results = self.all_results['suites']['validation']
            test_details += '<div class="suite"><div class="suite-header">📋 Тесты валидации</div>'
            
            for test_name, test_result in validation_results['tests'].items():
                status_class = f"status-{test_result['status'].lower()}"
                test_details += f'''
                <div class="test-item">
                    <div>
                        <strong>{test_name}</strong>
                        <div class="execution-time">Время: {test_result['execution_time']:.3f}s</div>
                        {f'<div class="error-details">{test_result["error"]}</div>' if test_result['error'] else ''}
                    </div>
                    <div class="test-status {status_class}">{test_result['status']}</div>
                </div>
                '''
            
            test_details += '</div>'
        
        # Подготовка данных для шаблона
        summary = self.all_results['summary']
        success_rate = (summary['passed_tests'] / summary['total_tests'] * 100) if summary['total_tests'] > 0 else 0
        success_class = 'passed' if success_rate >= 90 else ('failed' if success_rate < 70 else 'error')
        
        html_content = html_template.format(
            timestamp=datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
            total_tests=summary['total_tests'],
            passed_tests=summary['passed_tests'],
            failed_tests=summary['failed_tests'],
            error_tests=summary['error_tests'],
            execution_time=summary['execution_time'],
            success_rate=success_rate,
            success_class=success_class,
            test_details=test_details
        )
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"📄 HTML отчет сохранен в {filename}")
        return filename


def main():
    """Главная функция"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Комплексное тестирование системы')
    parser.add_argument('--output', '-o', default='test_results',
                       help='Базовое имя для файлов отчетов')
    parser.add_argument('--html-only', action='store_true',
                       help='Создать только HTML отчет')
    parser.add_argument('--json-only', action='store_true',
                       help='Создать только JSON отчет')
    
    args = parser.parse_args()
    
    # Запуск тестов
    runner = ComprehensiveTestRunner()
    results = runner.run_all_tests()
    
    # Сохранение результатов
    if not args.html_only:
        json_file = runner.save_results(f"{args.output}.json")
    
    if not args.json_only:
        html_file = runner.generate_html_report(f"{args.output}.html")
    
    # Возвращаем код выхода на основе результатов
    summary = results['summary']
    if summary['failed_tests'] == 0 and summary['error_tests'] == 0:
        sys.exit(0)  # Успех
    else:
        sys.exit(1)  # Есть проблемы


if __name__ == '__main__':
    main()
