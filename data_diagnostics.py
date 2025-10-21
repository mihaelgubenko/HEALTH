#!/usr/bin/env python
"""
Скрипт диагностики данных с HTML отчетом
Проверяет целостность данных, находит ошибки и предлагает исправления
"""

import os
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Tuple
import re

# Добавляем путь к Django проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_secretary.settings')

import django
django.setup()

from django.utils import timezone
from django.db.models import Count, Q
from core.models import Patient, Specialist, Service, Appointment, ContactMessage
from core.validators import ValidationManager, NameValidator, PhoneValidator


class DataDiagnostics:
    """Система диагностики данных с детальным анализом"""
    
    def __init__(self):
        self.validation_manager = ValidationManager()
        self.name_validator = NameValidator()
        self.phone_validator = PhoneValidator()
        
        self.report_data = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_issues': 0,
                'critical_issues': 0,
                'warnings': 0,
                'suggestions': 0
            },
            'sections': {}
        }
    
    def diagnose_patients(self) -> Dict[str, Any]:
        """Диагностика данных пациентов"""
        print("🔍 Диагностика пациентов...")
        
        issues = {
            'invalid_names': [],
            'invalid_phones': [],
            'duplicate_phones': [],
            'missing_data': [],
            'suspicious_patterns': []
        }
        
        patients = Patient.objects.all()
        
        for patient in patients:
            # Проверка имен
            name_valid, name_error = self.name_validator.validate_name(patient.name)
            if not name_valid:
                issues['invalid_names'].append({
                    'id': patient.id,
                    'name': patient.name,
                    'phone': patient.phone,
                    'error': name_error,
                    'suggestions': self.name_validator.suggest_corrections(patient.name)
                })
            
            # Проверка телефонов
            phone_valid, country, phone_result = self.phone_validator.validate_phone(patient.phone)
            if not phone_valid:
                issues['invalid_phones'].append({
                    'id': patient.id,
                    'name': patient.name,
                    'phone': patient.phone,
                    'error': phone_result,
                    'suggestions': self.phone_validator.suggest_corrections(patient.phone)
                })
            
            # Проверка обязательных полей
            if not patient.email and not patient.phone:
                issues['missing_data'].append({
                    'id': patient.id,
                    'name': patient.name,
                    'issue': 'Нет ни телефона, ни email'
                })
        
        # Поиск дубликатов телефонов
        duplicate_phones = Patient.objects.values('phone').annotate(
            count=Count('id')
        ).filter(count__gt=1, phone__isnull=False).exclude(phone='')
        
        for dup in duplicate_phones:
            duplicate_patients = Patient.objects.filter(phone=dup['phone'])
            issues['duplicate_phones'].append({
                'phone': dup['phone'],
                'count': dup['count'],
                'patients': [
                    {'id': p.id, 'name': p.name, 'created_at': p.created_at.isoformat()}
                    for p in duplicate_patients
                ]
            })
        
        # Поиск подозрительных паттернов
        suspicious_patterns = [
            r'^test',
            r'^тест',
            r'^admin',
            r'^админ',
            r'[a-z]{3,}\d+$',  # name123
            r'^\d+$',          # только цифры
            r'^[a-z]+$',       # только строчные буквы
        ]
        
        for patient in patients:
            for pattern in suspicious_patterns:
                if re.search(pattern, patient.name.lower()):
                    issues['suspicious_patterns'].append({
                        'id': patient.id,
                        'name': patient.name,
                        'phone': patient.phone,
                        'pattern': pattern,
                        'reason': 'Подозрительное имя'
                    })
                    break
        
        return {
            'total_patients': patients.count(),
            'issues': issues,
            'stats': {
                'invalid_names': len(issues['invalid_names']),
                'invalid_phones': len(issues['invalid_phones']),
                'duplicate_phones': len(issues['duplicate_phones']),
                'missing_data': len(issues['missing_data']),
                'suspicious_patterns': len(issues['suspicious_patterns'])
            }
        }
    
    def diagnose_appointments(self) -> Dict[str, Any]:
        """Диагностика записей"""
        print("🔍 Диагностика записей...")
        
        issues = {
            'past_appointments': [],
            'time_conflicts': [],
            'invalid_durations': [],
            'weekend_appointments': [],
            'holiday_appointments': [],
            'missing_end_time': [],
            'long_procedures': []
        }
        
        appointments = Appointment.objects.select_related(
            'patient', 'specialist', 'service'
        ).all()
        
        now = timezone.now()
        
        for appointment in appointments:
            # Записи в прошлом со статусом pending/confirmed
            if (appointment.start_time < now and 
                appointment.status in ['pending', 'confirmed']):
                issues['past_appointments'].append({
                    'id': appointment.id,
                    'patient': appointment.patient.name,
                    'specialist': appointment.specialist.name,
                    'start_time': appointment.start_time.isoformat(),
                    'status': appointment.status,
                    'days_ago': (now - appointment.start_time).days
                })
            
            # Записи на выходные
            if appointment.start_time.weekday() in [5, 6]:  # Сб, Вс
                issues['weekend_appointments'].append({
                    'id': appointment.id,
                    'patient': appointment.patient.name,
                    'specialist': appointment.specialist.name,
                    'start_time': appointment.start_time.isoformat(),
                    'weekday': appointment.start_time.strftime('%A')
                })
            
            # Отсутствует время окончания
            if not appointment.end_time:
                issues['missing_end_time'].append({
                    'id': appointment.id,
                    'patient': appointment.patient.name,
                    'start_time': appointment.start_time.isoformat()
                })
            
            # Слишком длинные процедуры (более 3 часов)
            if appointment.end_time:
                duration = appointment.end_time - appointment.start_time
                if duration.total_seconds() > 3 * 3600:  # 3 часа
                    issues['long_procedures'].append({
                        'id': appointment.id,
                        'patient': appointment.patient.name,
                        'specialist': appointment.specialist.name,
                        'start_time': appointment.start_time.isoformat(),
                        'duration_hours': duration.total_seconds() / 3600
                    })
        
        # Поиск конфликтов времени
        conflicts = self._find_time_conflicts()
        issues['time_conflicts'] = conflicts
        
        return {
            'total_appointments': appointments.count(),
            'issues': issues,
            'stats': {
                'past_appointments': len(issues['past_appointments']),
                'time_conflicts': len(issues['time_conflicts']),
                'weekend_appointments': len(issues['weekend_appointments']),
                'missing_end_time': len(issues['missing_end_time']),
                'long_procedures': len(issues['long_procedures'])
            }
        }
    
    def _find_time_conflicts(self) -> List[Dict[str, Any]]:
        """Поиск конфликтов времени между записями"""
        conflicts = []
        
        # Получаем все активные записи
        appointments = Appointment.objects.filter(
            status__in=['pending', 'confirmed']
        ).select_related('patient', 'specialist', 'service').order_by('start_time')
        
        # Группируем по специалистам
        specialists_appointments = {}
        for appointment in appointments:
            specialist_id = appointment.specialist.id
            if specialist_id not in specialists_appointments:
                specialists_appointments[specialist_id] = []
            specialists_appointments[specialist_id].append(appointment)
        
        # Проверяем конфликты для каждого специалиста
        for specialist_id, specialist_appointments in specialists_appointments.items():
            for i, apt1 in enumerate(specialist_appointments):
                for apt2 in specialist_appointments[i+1:]:
                    # Проверяем пересечение времени
                    if (apt1.start_time < apt2.end_time and 
                        apt1.end_time > apt2.start_time):
                        conflicts.append({
                            'specialist': apt1.specialist.name,
                            'appointment1': {
                                'id': apt1.id,
                                'patient': apt1.patient.name,
                                'start': apt1.start_time.isoformat(),
                                'end': apt1.end_time.isoformat() if apt1.end_time else None,
                                'service': apt1.service.name if apt1.service else 'Не указана'
                            },
                            'appointment2': {
                                'id': apt2.id,
                                'patient': apt2.patient.name,
                                'start': apt2.start_time.isoformat(),
                                'end': apt2.end_time.isoformat() if apt2.end_time else None,
                                'service': apt2.service.name if apt2.service else 'Не указана'
                            }
                        })
        
        return conflicts
    
    def diagnose_services_specialists(self) -> Dict[str, Any]:
        """Диагностика услуг и специалистов"""
        print("🔍 Диагностика услуг и специалистов...")
        
        issues = {
            'inactive_with_appointments': [],
            'missing_prices': [],
            'zero_duration': [],
            'unused_services': [],
            'unused_specialists': []
        }
        
        # Проверка услуг
        services = Service.objects.all()
        for service in services:
            # Неактивные услуги с записями
            if not service.is_active:
                active_appointments = Appointment.objects.filter(
                    service=service,
                    status__in=['pending', 'confirmed']
                ).count()
                if active_appointments > 0:
                    issues['inactive_with_appointments'].append({
                        'type': 'service',
                        'name': service.name,
                        'id': service.id,
                        'active_appointments': active_appointments
                    })
            
            # Отсутствует цена
            if not service.price or service.price <= 0:
                issues['missing_prices'].append({
                    'id': service.id,
                    'name': service.name,
                    'price': service.price
                })
            
            # Нулевая длительность
            if not service.duration or service.duration <= 0:
                issues['zero_duration'].append({
                    'id': service.id,
                    'name': service.name,
                    'duration': service.duration
                })
        
        # Неиспользуемые услуги
        unused_services = Service.objects.filter(
            appointment__isnull=True
        ).values('id', 'name', 'created_at')
        
        for service in unused_services:
            issues['unused_services'].append(service)
        
        # Проверка специалистов
        specialists = Specialist.objects.all()
        for specialist in specialists:
            # Неактивные специалисты с записями
            if not specialist.is_active:
                active_appointments = Appointment.objects.filter(
                    specialist=specialist,
                    status__in=['pending', 'confirmed']
                ).count()
                if active_appointments > 0:
                    issues['inactive_with_appointments'].append({
                        'type': 'specialist',
                        'name': specialist.name,
                        'id': specialist.id,
                        'active_appointments': active_appointments
                    })
        
        # Неиспользуемые специалисты
        unused_specialists = Specialist.objects.filter(
            appointment__isnull=True
        ).values('id', 'name', 'specialty', 'created_at')
        
        for specialist in unused_specialists:
            issues['unused_specialists'].append(specialist)
        
        return {
            'total_services': services.count(),
            'total_specialists': specialists.count(),
            'issues': issues,
            'stats': {
                'inactive_with_appointments': len(issues['inactive_with_appointments']),
                'missing_prices': len(issues['missing_prices']),
                'zero_duration': len(issues['zero_duration']),
                'unused_services': len(issues['unused_services']),
                'unused_specialists': len(issues['unused_specialists'])
            }
        }
    
    def diagnose_system_health(self) -> Dict[str, Any]:
        """Диагностика общего состояния системы"""
        print("🔍 Диагностика системы...")
        
        now = timezone.now()
        
        # Статистика по периодам
        today = now.date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        stats = {
            'appointments': {
                'total': Appointment.objects.count(),
                'today': Appointment.objects.filter(start_time__date=today).count(),
                'this_week': Appointment.objects.filter(start_time__date__gte=week_ago).count(),
                'this_month': Appointment.objects.filter(start_time__date__gte=month_ago).count(),
                'by_status': {}
            },
            'patients': {
                'total': Patient.objects.count(),
                'with_email': Patient.objects.exclude(email__isnull=True).exclude(email='').count(),
                'with_phone': Patient.objects.exclude(phone__isnull=True).exclude(phone='').count(),
                'recent': Patient.objects.filter(created_at__gte=week_ago).count()
            },
            'services': {
                'total': Service.objects.count(),
                'active': Service.objects.filter(is_active=True).count(),
                'with_appointments': Service.objects.filter(appointment__isnull=False).distinct().count()
            },
            'specialists': {
                'total': Specialist.objects.count(),
                'active': Specialist.objects.filter(is_active=True).count(),
                'with_appointments': Specialist.objects.filter(appointment__isnull=False).distinct().count()
            }
        }
        
        # Статистика по статусам записей
        status_counts = Appointment.objects.values('status').annotate(count=Count('id'))
        for status_count in status_counts:
            stats['appointments']['by_status'][status_count['status']] = status_count['count']
        
        # Проблемы производительности
        performance_issues = []
        
        # Слишком много записей на одну дату
        busy_dates = Appointment.objects.filter(
            start_time__date__gte=today
        ).values('start_time__date').annotate(
            count=Count('id')
        ).filter(count__gt=20).order_by('-count')
        
        for busy_date in busy_dates:
            performance_issues.append({
                'type': 'busy_date',
                'date': busy_date['start_time__date'].isoformat(),
                'appointments_count': busy_date['count'],
                'message': f"Слишком много записей на {busy_date['start_time__date']}: {busy_date['count']}"
            })
        
        return {
            'stats': stats,
            'performance_issues': performance_issues,
            'database_health': self._check_database_health()
        }
    
    def _check_database_health(self) -> Dict[str, Any]:
        """Проверка здоровья базы данных"""
        health = {
            'status': 'healthy',
            'issues': []
        }
        
        try:
            # Проверка подключения
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            
            # Проверка размера таблиц (для SQLite)
            if 'sqlite' in connection.settings_dict['ENGINE']:
                db_path = connection.settings_dict['NAME']
                if os.path.exists(db_path):
                    db_size = os.path.getsize(db_path)
                    health['database_size_mb'] = round(db_size / (1024 * 1024), 2)
                    
                    if db_size > 100 * 1024 * 1024:  # 100 MB
                        health['issues'].append("База данных превышает 100 MB")
                        health['status'] = 'warning'
        
        except Exception as e:
            health['status'] = 'error'
            health['issues'].append(f"Ошибка подключения к БД: {str(e)}")
        
        return health
    
    def generate_fixes(self) -> Dict[str, List[str]]:
        """Генерация предложений по исправлению"""
        fixes = {
            'critical': [],
            'recommended': [],
            'optional': []
        }
        
        # Анализируем найденные проблемы
        patients_data = self.report_data['sections'].get('patients', {})
        appointments_data = self.report_data['sections'].get('appointments', {})
        
        # Критические исправления
        if patients_data.get('stats', {}).get('invalid_phones', 0) > 0:
            fixes['critical'].append(
                "Исправить неверные номера телефонов пациентов - это критично для связи"
            )
        
        if appointments_data.get('stats', {}).get('time_conflicts', 0) > 0:
            fixes['critical'].append(
                "Устранить конфликты времени в записях - один специалист не может принимать двух пациентов одновременно"
            )
        
        # Рекомендуемые исправления
        if patients_data.get('stats', {}).get('duplicate_phones', 0) > 0:
            fixes['recommended'].append(
                "Объединить дубликаты пациентов с одинаковыми телефонами"
            )
        
        if appointments_data.get('stats', {}).get('past_appointments', 0) > 0:
            fixes['recommended'].append(
                "Обновить статусы прошедших записей на 'completed' или 'cancelled'"
            )
        
        # Опциональные улучшения
        if patients_data.get('stats', {}).get('invalid_names', 0) > 0:
            fixes['optional'].append(
                "Исправить некорректные имена пациентов для улучшения качества данных"
            )
        
        return fixes
    
    def run_full_diagnostics(self) -> Dict[str, Any]:
        """Запуск полной диагностики"""
        print("🚀 Запуск полной диагностики данных...")
        print("=" * 50)
        
        # Диагностика по разделам
        self.report_data['sections']['patients'] = self.diagnose_patients()
        self.report_data['sections']['appointments'] = self.diagnose_appointments()
        self.report_data['sections']['services_specialists'] = self.diagnose_services_specialists()
        self.report_data['sections']['system'] = self.diagnose_system_health()
        
        # Подсчет общих статистик
        total_issues = 0
        critical_issues = 0
        
        for section_name, section_data in self.report_data['sections'].items():
            if 'stats' in section_data:
                # Суммируем только числовые значения
                section_issues = sum(v for v in section_data['stats'].values() if isinstance(v, int))
                total_issues += section_issues
                
                # Критические проблемы
                if section_name == 'appointments':
                    critical_issues += section_data['stats'].get('time_conflicts', 0)
                    critical_issues += section_data['stats'].get('past_appointments', 0)
                elif section_name == 'patients':
                    critical_issues += section_data['stats'].get('invalid_phones', 0)
        
        self.report_data['summary']['total_issues'] = total_issues
        self.report_data['summary']['critical_issues'] = critical_issues
        
        # Генерация исправлений
        self.report_data['fixes'] = self.generate_fixes()
        
        print(f"✅ Диагностика завершена!")
        print(f"📊 Найдено проблем: {total_issues}")
        print(f"🚨 Критических: {critical_issues}")
        
        return self.report_data
    
    def generate_html_report(self, output_path: str = "data_diagnostics_report.html"):
        """Генерация HTML отчета"""
        print(f"📄 Генерация HTML отчета: {output_path}")
        
        html_template = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Отчет диагностики данных - Центр "Новая Жизнь"</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #4A90E2 0%, #27AE60 100%); color: white; padding: 30px; border-radius: 10px; margin-bottom: 30px; text-align: center; }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; }
        .header p { font-size: 1.2em; opacity: 0.9; }
        .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .summary-card { background: white; padding: 25px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center; }
        .summary-card h3 { color: #4A90E2; margin-bottom: 15px; }
        .summary-card .number { font-size: 3em; font-weight: bold; margin-bottom: 10px; }
        .critical { color: #E74C3C; }
        .warning { color: #F39C12; }
        .success { color: #27AE60; }
        .info { color: #3498DB; }
        .section { background: white; margin-bottom: 30px; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .section-header { background: #4A90E2; color: white; padding: 20px; font-size: 1.3em; font-weight: bold; }
        .section-content { padding: 25px; }
        .issue-list { list-style: none; }
        .issue-item { background: #f8f9fa; margin-bottom: 15px; padding: 15px; border-radius: 8px; border-left: 4px solid #E74C3C; }
        .issue-item.warning { border-left-color: #F39C12; }
        .issue-item.info { border-left-color: #3498DB; }
        .issue-title { font-weight: bold; margin-bottom: 8px; }
        .issue-details { color: #666; font-size: 0.9em; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }
        .stat-item { background: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center; }
        .stat-number { font-size: 2em; font-weight: bold; color: #4A90E2; }
        .stat-label { color: #666; font-size: 0.9em; }
        .fixes-section { background: linear-gradient(135deg, #27AE60 0%, #2ECC71 100%); color: white; padding: 25px; border-radius: 10px; margin-top: 30px; }
        .fixes-section h2 { margin-bottom: 20px; }
        .fix-category { margin-bottom: 20px; }
        .fix-category h3 { margin-bottom: 10px; }
        .fix-list { list-style: none; }
        .fix-list li { background: rgba(255,255,255,0.1); margin-bottom: 8px; padding: 10px; border-radius: 5px; }
        .timestamp { text-align: center; color: #666; margin-top: 30px; font-size: 0.9em; }
        .no-issues { text-align: center; color: #27AE60; font-size: 1.2em; padding: 40px; }
        .conflict-details { background: #fff3cd; padding: 15px; margin: 10px 0; border-radius: 5px; border: 1px solid #ffeaa7; }
        .patient-info { background: #e3f2fd; padding: 10px; margin: 5px 0; border-radius: 5px; }
        .suggestions { background: #e8f5e8; padding: 10px; margin: 10px 0; border-radius: 5px; border: 1px solid #c3e6c3; }
        .suggestions h4 { color: #27AE60; margin-bottom: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Отчет диагностики данных</h1>
            <p>Центр здоровья "Новая Жизнь"</p>
            <p>Создан: {timestamp}</p>
        </div>
        
        <div class="summary">
            <div class="summary-card">
                <h3>Всего проблем</h3>
                <div class="number {total_class}">{total_issues}</div>
            </div>
            <div class="summary-card">
                <h3>Критических</h3>
                <div class="number critical">{critical_issues}</div>
            </div>
            <div class="summary-card">
                <h3>Предупреждений</h3>
                <div class="number warning">{warnings}</div>
            </div>
            <div class="summary-card">
                <h3>Предложений</h3>
                <div class="number info">{suggestions}</div>
            </div>
        </div>
        
        {sections_html}
        
        {fixes_html}
        
        <div class="timestamp">
            Отчет сгенерирован автоматически системой диагностики данных<br>
            Время создания: {full_timestamp}
        </div>
    </div>
</body>
</html>
        """
        
        # Генерируем HTML для секций
        sections_html = ""
        
        for section_name, section_data in self.report_data['sections'].items():
            section_title = {
                'patients': '👥 Пациенты',
                'appointments': '📅 Записи',
                'services_specialists': '🏥 Услуги и специалисты',
                'system': '⚙️ Система'
            }.get(section_name, section_name.title())
            
            sections_html += f'<div class="section"><div class="section-header">{section_title}</div><div class="section-content">'
            
            # Статистика секции
            if 'stats' in section_data:
                sections_html += '<div class="stats-grid">'
                for stat_name, stat_value in section_data['stats'].items():
                    stat_label = stat_name.replace('_', ' ').title()
                    sections_html += f'''
                    <div class="stat-item">
                        <div class="stat-number">{stat_value}</div>
                        <div class="stat-label">{stat_label}</div>
                    </div>
                    '''
                sections_html += '</div>'
            
            # Проблемы секции
            if 'issues' in section_data:
                issues = section_data['issues']
                has_issues = any(len(issue_list) > 0 for issue_list in issues.values() if isinstance(issue_list, list))
                
                if has_issues:
                    sections_html += '<ul class="issue-list">'
                    
                    # Обработка разных типов проблем
                    for issue_type, issue_list in issues.items():
                        if not issue_list:
                            continue
                        
                        issue_title = {
                            'invalid_names': 'Некорректные имена',
                            'invalid_phones': 'Некорректные телефоны',
                            'duplicate_phones': 'Дубликаты телефонов',
                            'time_conflicts': 'Конфликты времени',
                            'past_appointments': 'Прошедшие записи',
                            'weekend_appointments': 'Записи на выходные',
                            'missing_end_time': 'Отсутствует время окончания',
                            'long_procedures': 'Слишком длинные процедуры'
                        }.get(issue_type, issue_type.replace('_', ' ').title())
                        
                        for issue in issue_list[:10]:  # Показываем только первые 10
                            sections_html += f'<li class="issue-item">'
                            sections_html += f'<div class="issue-title">{issue_title}</div>'
                            
                            # Детали проблемы
                            if issue_type == 'time_conflicts':
                                sections_html += f'''
                                <div class="conflict-details">
                                    <strong>Специалист:</strong> {issue['specialist']}<br>
                                    <div class="patient-info">
                                        <strong>Запись 1:</strong> {issue['appointment1']['patient']} 
                                        ({issue['appointment1']['start']} - {issue['appointment1']['end']})
                                    </div>
                                    <div class="patient-info">
                                        <strong>Запись 2:</strong> {issue['appointment2']['patient']} 
                                        ({issue['appointment2']['start']} - {issue['appointment2']['end']})
                                    </div>
                                </div>
                                '''
                            elif issue_type in ['invalid_names', 'invalid_phones']:
                                sections_html += f'''
                                <div class="issue-details">
                                    <strong>Пациент:</strong> {issue['name']} ({issue['phone']})<br>
                                    <strong>Ошибка:</strong> {issue['error']}
                                </div>
                                '''
                                if issue.get('suggestions'):
                                    sections_html += f'''
                                    <div class="suggestions">
                                        <h4>Предложения:</h4>
                                        {'; '.join(issue['suggestions'])}
                                    </div>
                                    '''
                            else:
                                # Общий формат для других типов проблем
                                sections_html += '<div class="issue-details">'
                                for key, value in issue.items():
                                    if key not in ['id', 'suggestions']:
                                        sections_html += f'<strong>{key.title()}:</strong> {value}<br>'
                                sections_html += '</div>'
                            
                            sections_html += '</li>'
                        
                        if len(issue_list) > 10:
                            sections_html += f'<li class="issue-item info"><div class="issue-title">И еще {len(issue_list) - 10} проблем этого типа...</div></li>'
                    
                    sections_html += '</ul>'
                else:
                    sections_html += '<div class="no-issues">✅ Проблем не обнаружено</div>'
            
            sections_html += '</div></div>'
        
        # Генерируем HTML для исправлений
        fixes_html = ""
        if 'fixes' in self.report_data:
            fixes_html = '<div class="fixes-section"><h2>🔧 Рекомендации по исправлению</h2>'
            
            for category, fix_list in self.report_data['fixes'].items():
                if fix_list:
                    category_title = {
                        'critical': '🚨 Критические исправления',
                        'recommended': '⚠️ Рекомендуемые исправления',
                        'optional': '💡 Опциональные улучшения'
                    }.get(category, category.title())
                    
                    fixes_html += f'<div class="fix-category"><h3>{category_title}</h3><ul class="fix-list">'
                    for fix in fix_list:
                        fixes_html += f'<li>{fix}</li>'
                    fixes_html += '</ul></div>'
            
            fixes_html += '</div>'
        
        # Подготовка данных для шаблона
        total_issues = self.report_data['summary']['total_issues']
        critical_issues = self.report_data['summary']['critical_issues']
        
        total_class = 'critical' if critical_issues > 0 else ('warning' if total_issues > 0 else 'success')
        
        html_content = html_template.format(
            timestamp=datetime.now().strftime('%d.%m.%Y %H:%M'),
            full_timestamp=datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
            total_issues=total_issues,
            critical_issues=critical_issues,
            warnings=total_issues - critical_issues,
            suggestions=len(self.report_data.get('fixes', {}).get('optional', [])),
            total_class=total_class,
            sections_html=sections_html,
            fixes_html=fixes_html
        )
        
        # Сохраняем отчет
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✅ HTML отчет сохранен: {output_path}")
        return output_path


def main():
    """Главная функция"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Диагностика данных медицинского центра')
    parser.add_argument('--output', '-o', default='data_diagnostics_report.html',
                       help='Путь для сохранения HTML отчета')
    parser.add_argument('--json', action='store_true',
                       help='Также сохранить JSON отчет')
    
    args = parser.parse_args()
    
    # Запуск диагностики
    diagnostics = DataDiagnostics()
    report_data = diagnostics.run_full_diagnostics()
    
    # Генерация HTML отчета
    html_path = diagnostics.generate_html_report(args.output)
    
    # Сохранение JSON отчета (если запрошено)
    if args.json:
        json_path = args.output.replace('.html', '.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False, default=str)
        print(f"✅ JSON отчет сохранен: {json_path}")
    
    # Вывод краткой сводки
    print("\n" + "=" * 50)
    print("📋 КРАТКАЯ СВОДКА")
    print("=" * 50)
    print(f"Всего проблем: {report_data['summary']['total_issues']}")
    print(f"Критических: {report_data['summary']['critical_issues']}")
    print(f"HTML отчет: {html_path}")
    
    if report_data['summary']['critical_issues'] > 0:
        print("\n🚨 ВНИМАНИЕ: Обнаружены критические проблемы!")
        print("Рекомендуется немедленно просмотреть отчет и принять меры.")
    elif report_data['summary']['total_issues'] > 0:
        print("\n⚠️ Обнаружены проблемы, требующие внимания.")
    else:
        print("\n✅ Критических проблем не обнаружено!")


if __name__ == '__main__':
    main()
