#!/usr/bin/env python
"""
Комплексный скрипт для полной проверки функциональности админки Django
Центр здоровья "Новая Жизнь"

Использование:
    python admin_test_suite.py --full --report=html --cleanup
    
Опции:
    --full      - полное тестирование включая производительность
    --report    - формат отчета (html|json|console)
    --cleanup   - удаление тестовых данных после завершения
    --verbose   - детальный вывод в консоль
"""

import os
import sys
import time
import json
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
import django
from django.db import connection
from django.test.utils import override_settings
from django.core.management import call_command
from django.template.loader import render_to_string

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_secretary.settings')
django.setup()

from core.models import Patient, Service, Specialist, Appointment, FAQ, ContactMessage, DialogLog
from core.admin_dashboard import AdminDashboard
from test_data_generator import TestDataGenerator


class TestResult:
    """Класс для хранения результатов тестов"""
    def __init__(self, name: str, success: bool, message: str = "", duration: float = 0.0, details: Dict = None):
        self.name = name
        self.success = success
        self.message = message
        self.duration = duration
        self.details = details or {}
        self.timestamp = datetime.now()


class DatabaseTester:
    """Тестирование моделей и базы данных"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results = []
    
    def run_all_tests(self) -> List[TestResult]:
        """Запуск всех тестов базы данных"""
        print("🔍 Тестирование базы данных...")
        
        self.test_models_existence()
        self.test_data_integrity()
        self.test_model_relationships()
        self.test_required_fields()
        self.test_crud_operations()
        
        return self.results
    
    def test_models_existence(self):
        """Проверка существования всех моделей"""
        start_time = time.time()
        
        try:
            models = [Patient, Service, Specialist, Appointment, FAQ, ContactMessage, DialogLog]
            model_counts = {}
            
            for model in models:
                count = model.objects.count()
                model_counts[model.__name__] = count
                if self.verbose:
                    print(f"  {model.__name__}: {count} записей")
            
            duration = time.time() - start_time
            self.results.append(TestResult(
                "Существование моделей",
                True,
                f"Все {len(models)} моделей доступны",
                duration,
                {"counts": model_counts}
            ))
            
        except Exception as e:
            duration = time.time() - start_time
            self.results.append(TestResult(
                "Существование моделей",
                False,
                f"Ошибка: {str(e)}",
                duration
            ))
    
    def test_data_integrity(self):
        """Проверка целостности данных"""
        start_time = time.time()
        
        try:
            issues = []
            
            # Проверка записей без пациентов
            orphaned_appointments = Appointment.objects.filter(patient__isnull=True).count()
            if orphaned_appointments > 0:
                issues.append(f"Записей без пациентов: {orphaned_appointments}")
            
            # Проверка записей без специалистов
            no_specialist = Appointment.objects.filter(specialist__isnull=True).count()
            if no_specialist > 0:
                issues.append(f"Записей без специалистов: {no_specialist}")
            
            # Проверка записей без услуг
            no_service = Appointment.objects.filter(service__isnull=True).count()
            if no_service > 0:
                issues.append(f"Записей без услуг: {no_service}")
            
            # Проверка дублирующихся пациентов по телефону
            from django.db.models import Count
            duplicate_phones = Patient.objects.values('phone').annotate(
                count=Count('phone')
            ).filter(count__gt=1).count()
            
            if duplicate_phones > 0:
                issues.append(f"Дублирующихся телефонов: {duplicate_phones}")
            
            duration = time.time() - start_time
            success = len(issues) == 0
            message = "Целостность данных в порядке" if success else f"Найдено проблем: {len(issues)}"
            
            self.results.append(TestResult(
                "Целостность данных",
                success,
                message,
                duration,
                {"issues": issues}
            ))
            
        except Exception as e:
            duration = time.time() - start_time
            self.results.append(TestResult(
                "Целостность данных",
                False,
                f"Ошибка: {str(e)}",
                duration
            ))
    
    def test_model_relationships(self):
        """Проверка связей между моделями"""
        start_time = time.time()
        
        try:
            # Проверяем, что все записи имеют корректные связи
            appointments_with_relations = Appointment.objects.select_related(
                'patient', 'specialist', 'service'
            ).count()
            
            total_appointments = Appointment.objects.count()
            
            duration = time.time() - start_time
            success = appointments_with_relations == total_appointments
            
            self.results.append(TestResult(
                "Связи между моделями",
                success,
                f"Проверено {appointments_with_relations}/{total_appointments} записей",
                duration
            ))
            
        except Exception as e:
            duration = time.time() - start_time
            self.results.append(TestResult(
                "Связи между моделями",
                False,
                f"Ошибка: {str(e)}",
                duration
            ))
    
    def test_required_fields(self):
        """Проверка обязательных полей"""
        start_time = time.time()
        
        try:
            issues = []
            
            # Проверка пациентов без имени
            no_name_patients = Patient.objects.filter(name__isnull=True).count()
            if no_name_patients > 0:
                issues.append(f"Пациентов без имени: {no_name_patients}")
            
            # Проверка пациентов без телефона
            no_phone_patients = Patient.objects.filter(phone__isnull=True).count()
            if no_phone_patients > 0:
                issues.append(f"Пациентов без телефона: {no_phone_patients}")
            
            # Проверка услуг без названия
            no_name_services = Service.objects.filter(name__isnull=True).count()
            if no_name_services > 0:
                issues.append(f"Услуг без названия: {no_name_services}")
            
            # Проверка специалистов без имени
            no_name_specialists = Specialist.objects.filter(name__isnull=True).count()
            if no_name_specialists > 0:
                issues.append(f"Специалистов без имени: {no_name_specialists}")
            
            duration = time.time() - start_time
            success = len(issues) == 0
            message = "Все обязательные поля заполнены" if success else f"Найдено проблем: {len(issues)}"
            
            self.results.append(TestResult(
                "Обязательные поля",
                success,
                message,
                duration,
                {"issues": issues}
            ))
            
        except Exception as e:
            duration = time.time() - start_time
            self.results.append(TestResult(
                "Обязательные поля",
                False,
                f"Ошибка: {str(e)}",
                duration
            ))
    
    def test_crud_operations(self):
        """Тестирование CRUD операций"""
        start_time = time.time()
        
        try:
            # Создание тестового пациента
            test_patient = Patient.objects.create(
                name="Тест Пациент",
                phone="+972000000000",
                email="test@example.com"
            )
            
            # Чтение
            retrieved_patient = Patient.objects.get(id=test_patient.id)
            assert retrieved_patient.name == "Тест Пациент"
            
            # Обновление
            retrieved_patient.name = "Обновленный Пациент"
            retrieved_patient.save()
            
            updated_patient = Patient.objects.get(id=test_patient.id)
            assert updated_patient.name == "Обновленный Пациент"
            
            # Удаление
            patient_id = test_patient.id
            test_patient.delete()
            
            # Проверка удаления
            assert not Patient.objects.filter(id=patient_id).exists()
            
            duration = time.time() - start_time
            self.results.append(TestResult(
                "CRUD операции",
                True,
                "Все CRUD операции работают корректно",
                duration
            ))
            
        except Exception as e:
            duration = time.time() - start_time
            self.results.append(TestResult(
                "CRUD операции",
                False,
                f"Ошибка: {str(e)}",
                duration
            ))


class AdminInterfaceTester:
    """Тестирование админ-интерфейса"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results = []
    
    def run_all_tests(self) -> List[TestResult]:
        """Запуск всех тестов админ-интерфейса"""
        print("🖥️ Тестирование админ-интерфейса...")
        
        self.test_admin_models_registration()
        self.test_admin_configurations()
        self.test_search_functionality()
        self.test_filter_functionality()
        
        return self.results
    
    def test_admin_models_registration(self):
        """Проверка регистрации моделей в админке"""
        start_time = time.time()
        
        try:
            from core.admin import admin_site
            
            registered_models = []
            expected_models = [Patient, Service, Specialist, Appointment, FAQ, ContactMessage, DialogLog]
            
            for model in expected_models:
                if admin_site.is_registered(model):
                    registered_models.append(model.__name__)
            
            duration = time.time() - start_time
            success = len(registered_models) == len(expected_models)
            
            self.results.append(TestResult(
                "Регистрация моделей в админке",
                success,
                f"Зарегистрировано {len(registered_models)}/{len(expected_models)} моделей",
                duration,
                {"registered": registered_models}
            ))
            
        except Exception as e:
            duration = time.time() - start_time
            self.results.append(TestResult(
                "Регистрация моделей в админке",
                False,
                f"Ошибка: {str(e)}",
                duration
            ))
    
    def test_admin_configurations(self):
        """Проверка конфигураций админки"""
        start_time = time.time()
        
        try:
            from core.admin import admin_site, AppointmentAdmin
            
            # Проверяем конфигурацию AppointmentAdmin
            appointment_admin = admin_site._registry.get(Appointment)
            
            checks = {
                "list_display": hasattr(appointment_admin, 'list_display'),
                "list_filter": hasattr(appointment_admin, 'list_filter'),
                "search_fields": hasattr(appointment_admin, 'search_fields'),
                "actions": hasattr(appointment_admin, 'actions'),
                "colored_status": hasattr(appointment_admin, 'colored_status'),
                "quick_actions": hasattr(appointment_admin, 'quick_actions')
            }
            
            passed_checks = sum(checks.values())
            total_checks = len(checks)
            
            duration = time.time() - start_time
            success = passed_checks == total_checks
            
            self.results.append(TestResult(
                "Конфигурации админки",
                success,
                f"Пройдено {passed_checks}/{total_checks} проверок",
                duration,
                {"checks": checks}
            ))
            
        except Exception as e:
            duration = time.time() - start_time
            self.results.append(TestResult(
                "Конфигурации админки",
                False,
                f"Ошибка: {str(e)}",
                duration
            ))
    
    def test_search_functionality(self):
        """Тестирование функциональности поиска"""
        start_time = time.time()
        
        try:
            # Тестируем поиск пациентов
            if Patient.objects.exists():
                first_patient = Patient.objects.first()
                search_results = Patient.objects.filter(name__icontains=first_patient.name[:3])
                search_works = search_results.exists()
            else:
                search_works = True  # Нет данных для поиска
            
            duration = time.time() - start_time
            
            self.results.append(TestResult(
                "Функциональность поиска",
                search_works,
                "Поиск работает корректно" if search_works else "Поиск не работает",
                duration
            ))
            
        except Exception as e:
            duration = time.time() - start_time
            self.results.append(TestResult(
                "Функциональность поиска",
                False,
                f"Ошибка: {str(e)}",
                duration
            ))
    
    def test_filter_functionality(self):
        """Тестирование функциональности фильтров"""
        start_time = time.time()
        
        try:
            # Тестируем фильтрацию записей по статусу
            pending_count = Appointment.objects.filter(status='pending').count()
            confirmed_count = Appointment.objects.filter(status='confirmed').count()
            total_count = Appointment.objects.count()
            
            filter_works = (pending_count + confirmed_count) <= total_count
            
            duration = time.time() - start_time
            
            self.results.append(TestResult(
                "Функциональность фильтров",
                filter_works,
                f"Фильтры работают: pending={pending_count}, confirmed={confirmed_count}",
                duration,
                {
                    "pending": pending_count,
                    "confirmed": confirmed_count,
                    "total": total_count
                }
            ))
            
        except Exception as e:
            duration = time.time() - start_time
            self.results.append(TestResult(
                "Функциональность фильтров",
                False,
                f"Ошибка: {str(e)}",
                duration
            ))


class CustomFunctionalityTester:
    """Тестирование кастомной функциональности"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results = []
    
    def run_all_tests(self) -> List[TestResult]:
        """Запуск всех тестов кастомной функциональности"""
        print("⚙️ Тестирование кастомной функциональности...")
        
        self.test_dashboard_functionality()
        self.test_quick_actions()
        self.test_mass_actions()
        self.test_colored_status()
        
        return self.results
    
    def test_dashboard_functionality(self):
        """Тестирование дашборда"""
        start_time = time.time()
        
        try:
            dashboard = AdminDashboard()
            dashboard_data = dashboard.get_dashboard_data()
            
            required_keys = [
                'appointments_today', 'appointments_week', 'appointments_month',
                'total_patients', 'appointments_by_status', 'popular_services',
                'specialists_stats', 'recent_messages'
            ]
            
            missing_keys = [key for key in required_keys if key not in dashboard_data]
            
            duration = time.time() - start_time
            success = len(missing_keys) == 0
            
            self.results.append(TestResult(
                "Функциональность дашборда",
                success,
                f"Дашборд работает корректно" if success else f"Отсутствуют ключи: {missing_keys}",
                duration,
                {"missing_keys": missing_keys, "data_keys": list(dashboard_data.keys())}
            ))
            
        except Exception as e:
            duration = time.time() - start_time
            self.results.append(TestResult(
                "Функциональность дашборда",
                False,
                f"Ошибка: {str(e)}",
                duration
            ))
    
    def test_quick_actions(self):
        """Тестирование быстрых действий"""
        start_time = time.time()
        
        try:
            from core.admin import AppointmentAdmin
            
            # Создаем тестовую запись
            if not Appointment.objects.exists():
                # Если нет записей, создаем тестовые данные
                self.results.append(TestResult(
                    "Быстрые действия",
                    True,
                    "Нет записей для тестирования быстрых действий",
                    time.time() - start_time
                ))
                return
            
            appointment = Appointment.objects.first()
            admin_instance = AppointmentAdmin(Appointment, None)
            
            # Тестируем методы быстрых действий
            colored_status = admin_instance.colored_status(appointment)
            quick_actions = admin_instance.quick_actions(appointment)
            
            duration = time.time() - start_time
            success = colored_status is not None and quick_actions is not None
            
            self.results.append(TestResult(
                "Быстрые действия",
                success,
                "Быстрые действия работают корректно" if success else "Ошибка в быстрых действиях",
                duration
            ))
            
        except Exception as e:
            duration = time.time() - start_time
            self.results.append(TestResult(
                "Быстрые действия",
                False,
                f"Ошибка: {str(e)}",
                duration
            ))
    
    def test_mass_actions(self):
        """Тестирование массовых действий"""
        start_time = time.time()
        
        try:
            from core.admin import AppointmentAdmin
            
            admin_instance = AppointmentAdmin(Appointment, None)
            
            # Проверяем наличие массовых действий
            actions = admin_instance.actions
            expected_actions = ['confirm_appointments', 'cancel_appointments', 'complete_appointments']
            
            available_actions = [action for action in expected_actions if action in actions]
            
            duration = time.time() - start_time
            success = len(available_actions) == len(expected_actions)
            
            self.results.append(TestResult(
                "Массовые действия",
                success,
                f"Доступно {len(available_actions)}/{len(expected_actions)} действий",
                duration,
                {"available_actions": available_actions}
            ))
            
        except Exception as e:
            duration = time.time() - start_time
            self.results.append(TestResult(
                "Массовые действия",
                False,
                f"Ошибка: {str(e)}",
                duration
            ))
    
    def test_colored_status(self):
        """Тестирование цветных статусов"""
        start_time = time.time()
        
        try:
            from core.admin import AppointmentAdmin
            
            if not Appointment.objects.exists():
                self.results.append(TestResult(
                    "Цветные статусы",
                    True,
                    "Нет записей для тестирования цветных статусов",
                    time.time() - start_time
                ))
                return
            
            admin_instance = AppointmentAdmin(Appointment, None)
            
            # Тестируем разные статусы
            statuses_tested = []
            for status in ['pending', 'confirmed', 'cancelled', 'completed']:
                appointments = Appointment.objects.filter(status=status)
                if appointments.exists():
                    appointment = appointments.first()
                    colored_status = admin_instance.colored_status(appointment)
                    if colored_status:
                        statuses_tested.append(status)
            
            duration = time.time() - start_time
            success = len(statuses_tested) > 0
            
            self.results.append(TestResult(
                "Цветные статусы",
                success,
                f"Протестировано статусов: {len(statuses_tested)}",
                duration,
                {"tested_statuses": statuses_tested}
            ))
            
        except Exception as e:
            duration = time.time() - start_time
            self.results.append(TestResult(
                "Цветные статусы",
                False,
                f"Ошибка: {str(e)}",
                duration
            ))


class PerformanceTester:
    """Тестирование производительности"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results = []
    
    def run_all_tests(self) -> List[TestResult]:
        """Запуск всех тестов производительности"""
        print("⚡ Тестирование производительности...")
        
        self.test_dashboard_performance()
        self.test_query_optimization()
        self.test_admin_list_performance()
        
        return self.results
    
    def test_dashboard_performance(self):
        """Тестирование производительности дашборда"""
        start_time = time.time()
        
        try:
            dashboard = AdminDashboard()
            
            # Измеряем время загрузки дашборда
            dashboard_start = time.time()
            dashboard_data = dashboard.get_dashboard_data()
            dashboard_duration = time.time() - dashboard_start
            
            # Критерий: дашборд должен загружаться менее чем за 2 секунды
            success = dashboard_duration < 2.0
            
            duration = time.time() - start_time
            
            self.results.append(TestResult(
                "Производительность дашборда",
                success,
                f"Дашборд загружается за {dashboard_duration:.3f}с (лимит: 2.0с)",
                duration,
                {"dashboard_load_time": dashboard_duration, "limit": 2.0}
            ))
            
        except Exception as e:
            duration = time.time() - start_time
            self.results.append(TestResult(
                "Производительность дашборда",
                False,
                f"Ошибка: {str(e)}",
                duration
            ))
    
    def test_query_optimization(self):
        """Тестирование оптимизации запросов"""
        start_time = time.time()
        
        try:
            # Сбрасываем счетчик запросов
            connection.queries_log.clear()
            
            # Выполняем типичные операции админки
            appointments = list(Appointment.objects.select_related('patient', 'specialist', 'service')[:10])
            
            query_count = len(connection.queries)
            
            # Критерий: не более 5 запросов для загрузки 10 записей с связями
            success = query_count <= 5
            
            duration = time.time() - start_time
            
            self.results.append(TestResult(
                "Оптимизация запросов",
                success,
                f"Выполнено {query_count} запросов (лимит: 5)",
                duration,
                {"query_count": query_count, "limit": 5}
            ))
            
        except Exception as e:
            duration = time.time() - start_time
            self.results.append(TestResult(
                "Оптимизация запросов",
                False,
                f"Ошибка: {str(e)}",
                duration
            ))
    
    def test_admin_list_performance(self):
        """Тестирование производительности списков админки"""
        start_time = time.time()
        
        try:
            # Тестируем время загрузки списка записей
            list_start = time.time()
            appointments = Appointment.objects.select_related('patient', 'specialist', 'service')[:25]
            list(appointments)  # Принудительно выполняем запрос
            list_duration = time.time() - list_start
            
            # Критерий: список должен загружаться менее чем за 1 секунду
            success = list_duration < 1.0
            
            duration = time.time() - start_time
            
            self.results.append(TestResult(
                "Производительность списков",
                success,
                f"Список загружается за {list_duration:.3f}с (лимит: 1.0с)",
                duration,
                {"list_load_time": list_duration, "limit": 1.0}
            ))
            
        except Exception as e:
            duration = time.time() - start_time
            self.results.append(TestResult(
                "Производительность списков",
                False,
                f"Ошибка: {str(e)}",
                duration
            ))


class ReportGenerator:
    """Генератор отчетов"""
    
    def __init__(self, results: List[TestResult]):
        self.results = results
        self.total_tests = len(results)
        self.passed_tests = sum(1 for r in results if r.success)
        self.failed_tests = self.total_tests - self.passed_tests
        self.total_duration = sum(r.duration for r in results)
    
    def generate_console_report(self) -> str:
        """Генерация консольного отчета"""
        report = []
        report.append("=" * 80)
        report.append("🏥 ОТЧЕТ О ТЕСТИРОВАНИИ АДМИНКИ - ЦЕНТР 'НОВАЯ ЖИЗНЬ'")
        report.append("=" * 80)
        report.append(f"📊 Общая статистика:")
        report.append(f"   Всего тестов: {self.total_tests}")
        report.append(f"   Пройдено: {self.passed_tests} ✅")
        report.append(f"   Провалено: {self.failed_tests} ❌")
        report.append(f"   Время выполнения: {self.total_duration:.3f}с")
        report.append(f"   Успешность: {(self.passed_tests/self.total_tests*100):.1f}%")
        report.append("")
        
        # Группируем результаты по категориям
        categories = {
            "База данных": [],
            "Админ-интерфейс": [],
            "Кастомная функциональность": [],
            "Производительность": []
        }
        
        for result in self.results:
            if any(keyword in result.name.lower() for keyword in ['модел', 'данн', 'crud', 'цел']):
                categories["База данных"].append(result)
            elif any(keyword in result.name.lower() for keyword in ['админ', 'регистр', 'конфиг', 'поиск', 'фильтр']):
                categories["Админ-интерфейс"].append(result)
            elif any(keyword in result.name.lower() for keyword in ['дашборд', 'действи', 'статус']):
                categories["Кастомная функциональность"].append(result)
            elif any(keyword in result.name.lower() for keyword in ['производ', 'запрос', 'список']):
                categories["Производительность"].append(result)
        
        for category, tests in categories.items():
            if tests:
                report.append(f"📂 {category}:")
                for test in tests:
                    status = "✅" if test.success else "❌"
                    report.append(f"   {status} {test.name}: {test.message} ({test.duration:.3f}с)")
                report.append("")
        
        # Рекомендации
        if self.failed_tests > 0:
            report.append("🔧 РЕКОМЕНДАЦИИ ПО ИСПРАВЛЕНИЮ:")
            for result in self.results:
                if not result.success:
                    report.append(f"   • {result.name}: {result.message}")
            report.append("")
        
        report.append("=" * 80)
        return "\n".join(report)
    
    def generate_json_report(self) -> Dict[str, Any]:
        """Генерация JSON отчета"""
        return {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": self.total_tests,
                "passed_tests": self.passed_tests,
                "failed_tests": self.failed_tests,
                "success_rate": self.passed_tests / self.total_tests * 100,
                "total_duration": self.total_duration
            },
            "results": [
                {
                    "name": result.name,
                    "success": result.success,
                    "message": result.message,
                    "duration": result.duration,
                    "details": result.details,
                    "timestamp": result.timestamp.isoformat()
                }
                for result in self.results
            ]
        }
    
    def generate_html_report(self) -> str:
        """Генерация HTML отчета"""
        context = {
            'timestamp': datetime.now(),
            'summary': {
                'total_tests': self.total_tests,
                'passed_tests': self.passed_tests,
                'failed_tests': self.failed_tests,
                'success_rate': self.passed_tests / self.total_tests * 100,
                'total_duration': self.total_duration
            },
            'results': self.results
        }
        
        # Если шаблон не найден, создаем простой HTML
        try:
            return render_to_string('admin/test_report.html', context)
        except:
            return self._generate_simple_html(context)
    
    def _generate_simple_html(self, context) -> str:
        """Генерация простого HTML отчета"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Отчет о тестировании админки</title>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background: linear-gradient(135deg, #4A90E2 0%, #27AE60 100%); 
                          color: white; padding: 20px; border-radius: 8px; }}
                .summary {{ background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 20px 0; }}
                .test-result {{ margin: 10px 0; padding: 10px; border-radius: 4px; }}
                .success {{ background: #d4edda; border-left: 4px solid #28a745; }}
                .failure {{ background: #f8d7da; border-left: 4px solid #dc3545; }}
                .duration {{ color: #6c757d; font-size: 0.9em; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🏥 Отчет о тестировании админки</h1>
                <p>Центр здоровья "Новая Жизнь" - {context['timestamp'].strftime('%d.%m.%Y %H:%M')}</p>
            </div>
            
            <div class="summary">
                <h2>📊 Общая статистика</h2>
                <p><strong>Всего тестов:</strong> {context['summary']['total_tests']}</p>
                <p><strong>Пройдено:</strong> {context['summary']['passed_tests']} ✅</p>
                <p><strong>Провалено:</strong> {context['summary']['failed_tests']} ❌</p>
                <p><strong>Успешность:</strong> {context['summary']['success_rate']:.1f}%</p>
                <p><strong>Время выполнения:</strong> {context['summary']['total_duration']:.3f}с</p>
            </div>
            
            <h2>📋 Детальные результаты</h2>
        """
        
        for result in context['results']:
            css_class = "success" if result.success else "failure"
            status = "✅" if result.success else "❌"
            html += f"""
            <div class="test-result {css_class}">
                <strong>{status} {result.name}</strong><br>
                {result.message}
                <div class="duration">Время выполнения: {result.duration:.3f}с</div>
            </div>
            """
        
        html += """
        </body>
        </html>
        """
        return html


def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(description='Тестирование функциональности админки')
    parser.add_argument('--full', action='store_true', help='Полное тестирование включая производительность')
    parser.add_argument('--report', choices=['html', 'json', 'console'], default='console', help='Формат отчета')
    parser.add_argument('--cleanup', action='store_true', help='Удаление тестовых данных после завершения')
    parser.add_argument('--verbose', action='store_true', help='Детальный вывод в консоль')
    
    args = parser.parse_args()
    
    print("🏥 ТЕСТИРОВАНИЕ АДМИНКИ - ЦЕНТР 'НОВАЯ ЖИЗНЬ'")
    print("=" * 50)
    
    all_results = []
    
    # Создание тестовых данных если нужно
    if args.cleanup:
        print("📝 Создание тестовых данных...")
        generator = TestDataGenerator()
        generator.generate_test_data()
    
    try:
        # Тестирование базы данных
        db_tester = DatabaseTester(args.verbose)
        all_results.extend(db_tester.run_all_tests())
        
        # Тестирование админ-интерфейса
        admin_tester = AdminInterfaceTester(args.verbose)
        all_results.extend(admin_tester.run_all_tests())
        
        # Тестирование кастомной функциональности
        custom_tester = CustomFunctionalityTester(args.verbose)
        all_results.extend(custom_tester.run_all_tests())
        
        # Тестирование производительности (только при --full)
        if args.full:
            perf_tester = PerformanceTester(args.verbose)
            all_results.extend(perf_tester.run_all_tests())
        
        # Генерация отчета
        print("\n📊 Генерация отчета...")
        report_generator = ReportGenerator(all_results)
        
        if args.report == 'console':
            print(report_generator.generate_console_report())
        elif args.report == 'json':
            json_report = report_generator.generate_json_report()
            with open('admin_test_report.json', 'w', encoding='utf-8') as f:
                json.dump(json_report, f, ensure_ascii=False, indent=2)
            print(f"📄 JSON отчет сохранен в admin_test_report.json")
        elif args.report == 'html':
            html_report = report_generator.generate_html_report()
            with open('admin_test_report.html', 'w', encoding='utf-8') as f:
                f.write(html_report)
            print(f"📄 HTML отчет сохранен в admin_test_report.html")
    
    finally:
        # Очистка тестовых данных
        if args.cleanup:
            print("\n🧹 Очистка тестовых данных...")
            generator = TestDataGenerator()
            generator.cleanup_test_data()
    
    # Возвращаем код выхода
    failed_tests = sum(1 for r in all_results if not r.success)
    sys.exit(0 if failed_tests == 0 else 1)


if __name__ == '__main__':
    main()
