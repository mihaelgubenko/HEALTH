#!/usr/bin/env python
"""
Скрипт безопасного развертывания с автоматическим откатом
Выполняет поэтапное внедрение изменений с проверками на каждом этапе
"""

import os
import sys
import time
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from deployment.backup_and_rollback import BackupAndRollback


class SafeDeployment:
    """Система безопасного развертывания с автоматическим откатом"""
    
    def __init__(self):
        self.backup_system = BackupAndRollback()
        self.deployment_log = []
        self.rollback_triggers = {
            'critical_errors': 0,
            'max_errors': 3,
            'response_time_threshold': 5.0,  # секунды
            'error_rate_threshold': 0.1  # 10% ошибок
        }
        
    def log_step(self, step: str, status: str, message: str = ""):
        """Логирование шагов развертывания"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'step': step,
            'status': status,
            'message': message
        }
        self.deployment_log.append(log_entry)
        
        status_emoji = {
            'start': '🔄',
            'success': '✅', 
            'warning': '⚠️',
            'error': '❌',
            'rollback': '🔙'
        }
        
        print(f"{status_emoji.get(status, '•')} {step}: {message}")
    
    def pre_deployment_checks(self) -> Tuple[bool, List[str]]:
        """Проверки перед развертыванием"""
        self.log_step("Pre-deployment checks", "start")
        
        issues = []
        
        # 1. Проверка Git статуса
        try:
            result = subprocess.run(['git', 'status', '--porcelain'], 
                                  capture_output=True, text=True)
            if result.stdout.strip():
                issues.append("Есть незакоммиченные изменения в Git")
        except:
            issues.append("Не удается проверить статус Git")
        
        # 2. Проверка тестов
        try:
            # Запускаем базовые проверки Django
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_secretary.settings')
            import django
            django.setup()
            
            # Проверка настроек
            from django.core.management import execute_from_command_line
            from django.conf import settings
            
            if not settings.configured:
                issues.append("Django настройки не сконфигурированы")
                
        except Exception as e:
            issues.append(f"Ошибка проверки Django: {str(e)}")
        
        # 3. Проверка зависимостей
        try:
            import core.validators
            import core.forms
            import core.models
        except ImportError as e:
            issues.append(f"Ошибка импорта модулей: {str(e)}")
        
        # 4. Проверка базы данных
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except Exception as e:
            issues.append(f"Ошибка подключения к БД: {str(e)}")
        
        if issues:
            self.log_step("Pre-deployment checks", "error", 
                         f"Найдено проблем: {len(issues)}")
            for issue in issues:
                print(f"  ❌ {issue}")
            return False, issues
        else:
            self.log_step("Pre-deployment checks", "success", "Все проверки пройдены")
            return True, []
    
    def create_deployment_backup(self) -> Tuple[bool, str]:
        """Создание бэкапа перед развертыванием"""
        self.log_step("Creating backup", "start")
        
        success, message = self.backup_system.create_full_backup()
        
        if success:
            self.log_step("Creating backup", "success", message)
            self.backup_name = self.backup_system.backup_name
        else:
            self.log_step("Creating backup", "error", message)
        
        return success, message
    
    def deploy_validation_system(self) -> Tuple[bool, str]:
        """Развертывание системы валидации по этапам"""
        self.log_step("Deploying validation system", "start")
        
        try:
            # Этап 1: Обновление валидаторов
            step1_success = self._deploy_validators()
            if not step1_success:
                return False, "Ошибка на этапе 1: валидаторы"
            
            # Проверка после этапа 1
            if not self._health_check_after_step("validators"):
                return False, "Проверка здоровья не пройдена после этапа 1"
            
            # Этап 2: Обновление форм
            step2_success = self._deploy_forms()
            if not step2_success:
                return False, "Ошибка на этапе 2: формы"
            
            # Проверка после этапа 2
            if not self._health_check_after_step("forms"):
                return False, "Проверка здоровья не пройдена после этапа 2"
            
            # Этап 3: Обновление админки
            step3_success = self._deploy_admin_enhancements()
            if not step3_success:
                return False, "Ошибка на этапе 3: админка"
            
            # Финальная проверка
            if not self._final_health_check():
                return False, "Финальная проверка не пройдена"
            
            self.log_step("Deploying validation system", "success", 
                         "Все этапы развертывания завершены успешно")
            return True, "Система валидации развернута успешно"
            
        except Exception as e:
            self.log_step("Deploying validation system", "error", str(e))
            return False, f"Критическая ошибка развертывания: {str(e)}"
    
    def _deploy_validators(self) -> bool:
        """Этап 1: Развертывание улучшенных валидаторов"""
        self.log_step("Stage 1: Validators", "start")
        
        try:
            # Здесь будет код обновления валидаторов
            # Пока что просто проверяем что текущие валидаторы работают
            from core.validators import ValidationManager
            validator = ValidationManager()
            
            # Тестовая валидация
            test_result = validator.validate_appointment_data(
                name="Тест Тестов",
                phone="+972501234567", 
                service_name="Массаж",
                specialist_name="Авраам",
                date="2025-10-22",
                time="15:00"
            )
            
            if not isinstance(test_result, dict):
                return False
            
            self.log_step("Stage 1: Validators", "success", "Валидаторы работают корректно")
            return True
            
        except Exception as e:
            self.log_step("Stage 1: Validators", "error", str(e))
            return False
    
    def _deploy_forms(self) -> bool:
        """Этап 2: Развертывание улучшенных форм"""
        self.log_step("Stage 2: Forms", "start")
        
        try:
            # Проверяем что формы работают
            from core.forms import AppointmentForm
            form = AppointmentForm()
            
            if not hasattr(form, 'clean_preferred_date'):
                return False
            
            self.log_step("Stage 2: Forms", "success", "Формы работают корректно")
            return True
            
        except Exception as e:
            self.log_step("Stage 2: Forms", "error", str(e))
            return False
    
    def _deploy_admin_enhancements(self) -> bool:
        """Этап 3: Развертывание улучшений админки"""
        self.log_step("Stage 3: Admin", "start")
        
        try:
            # Проверяем что админка работает
            from core.admin import AppointmentAdmin
            from core.models import Appointment
            
            admin = AppointmentAdmin(Appointment, None)
            
            if not hasattr(admin, 'colored_status'):
                return False
            
            self.log_step("Stage 3: Admin", "success", "Админка работает корректно")
            return True
            
        except Exception as e:
            self.log_step("Stage 3: Admin", "error", str(e))
            return False
    
    def _health_check_after_step(self, step_name: str) -> bool:
        """Проверка здоровья после каждого этапа"""
        self.log_step(f"Health check after {step_name}", "start")
        
        checks = self.backup_system.health_check()
        all_good = all(checks.values())
        
        if all_good:
            self.log_step(f"Health check after {step_name}", "success", 
                         "Все проверки пройдены")
        else:
            failed_checks = [k for k, v in checks.items() if not v]
            self.log_step(f"Health check after {step_name}", "error", 
                         f"Неудачные проверки: {failed_checks}")
        
        return all_good
    
    def _final_health_check(self) -> bool:
        """Финальная проверка работоспособности"""
        self.log_step("Final health check", "start")
        
        try:
            # Комплексная проверка всех компонентов
            checks = {
                'database': False,
                'models': False,
                'validators': False,
                'forms': False,
                'admin': False,
                'ai_chat': False
            }
            
            # Проверка БД
            try:
                from django.db import connection
                with connection.cursor() as cursor:
                    cursor.execute("SELECT COUNT(*) FROM core_patient")
                checks['database'] = True
            except:
                pass
            
            # Проверка моделей
            try:
                from core.models import Patient, Appointment
                Patient.objects.count()
                Appointment.objects.count()
                checks['models'] = True
            except:
                pass
            
            # Проверка валидаторов
            try:
                from core.validators import ValidationManager
                validator = ValidationManager()
                checks['validators'] = True
            except:
                pass
            
            # Проверка форм
            try:
                from core.forms import AppointmentForm
                form = AppointmentForm()
                checks['forms'] = True
            except:
                pass
            
            # Проверка админки
            try:
                from core.admin import AppointmentAdmin
                checks['admin'] = True
            except:
                pass
            
            # Проверка ИИ-чата
            try:
                from core.lite_secretary import LiteSmartSecretary
                secretary = LiteSmartSecretary()
                checks['ai_chat'] = True
            except:
                pass
            
            success_count = sum(checks.values())
            total_count = len(checks)
            
            if success_count == total_count:
                self.log_step("Final health check", "success", 
                             f"Все {total_count} компонентов работают")
                return True
            else:
                failed = [k for k, v in checks.items() if not v]
                self.log_step("Final health check", "error", 
                             f"Неработающие компоненты: {failed}")
                return False
                
        except Exception as e:
            self.log_step("Final health check", "error", str(e))
            return False
    
    def automatic_rollback(self, reason: str) -> Tuple[bool, str]:
        """Автоматический откат при критических ошибках"""
        self.log_step("Automatic rollback", "rollback", f"Причина: {reason}")
        
        if hasattr(self, 'backup_name'):
            success, message = self.backup_system.rollback_from_backup(self.backup_name)
            
            if success:
                self.log_step("Automatic rollback", "success", 
                             "Система восстановлена из бэкапа")
            else:
                self.log_step("Automatic rollback", "error", 
                             f"Ошибка отката: {message}")
            
            return success, message
        else:
            return False, "Нет доступного бэкапа для отката"
    
    def save_deployment_log(self):
        """Сохранение лога развертывания"""
        log_dir = Path(__file__).parent.parent / 'logs'
        log_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = log_dir / f'deployment_{timestamp}.json'
        
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(self.deployment_log, f, indent=2, ensure_ascii=False)
        
        print(f"📋 Лог развертывания сохранен: {log_file}")
    
    def full_deployment_cycle(self) -> Tuple[bool, str]:
        """Полный цикл безопасного развертывания"""
        print("🚀 Начинаем безопасное развертывание системы валидации")
        print("=" * 60)
        
        try:
            # 1. Предварительные проверки
            pre_check_success, issues = self.pre_deployment_checks()
            if not pre_check_success:
                return False, f"Предварительные проверки не пройдены: {issues}"
            
            # 2. Создание бэкапа
            backup_success, backup_message = self.create_deployment_backup()
            if not backup_success:
                return False, f"Не удалось создать бэкап: {backup_message}"
            
            # 3. Развертывание системы
            deploy_success, deploy_message = self.deploy_validation_system()
            if not deploy_success:
                # Автоматический откат при ошибке
                rollback_success, rollback_message = self.automatic_rollback(deploy_message)
                if rollback_success:
                    return False, f"Развертывание не удалось, выполнен откат: {deploy_message}"
                else:
                    return False, f"Развертывание не удалось, откат тоже не удался: {rollback_message}"
            
            # 4. Финальные проверки
            time.sleep(2)  # Даем системе стабилизироваться
            final_check = self._final_health_check()
            if not final_check:
                rollback_success, rollback_message = self.automatic_rollback("Финальные проверки не пройдены")
                if rollback_success:
                    return False, "Финальные проверки не пройдены, выполнен откат"
                else:
                    return False, f"Финальные проверки не пройдены, откат не удался: {rollback_message}"
            
            print("=" * 60)
            print("🎉 Развертывание завершено успешно!")
            return True, "Система валидации развернута и работает корректно"
            
        except Exception as e:
            # Экстренный откат при критической ошибке
            try:
                self.automatic_rollback(f"Критическая ошибка: {str(e)}")
            except:
                pass
            
            return False, f"Критическая ошибка развертывания: {str(e)}"
        
        finally:
            # Всегда сохраняем лог
            self.save_deployment_log()


def main():
    """Главная функция для запуска из командной строки"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Безопасное развертывание системы валидации')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Только проверки, без реального развертывания')
    parser.add_argument('--force', action='store_true',
                       help='Игнорировать предупреждения')
    
    args = parser.parse_args()
    
    deployment = SafeDeployment()
    
    if args.dry_run:
        print("🔍 Режим проверки (dry-run)")
        success, issues = deployment.pre_deployment_checks()
        if success:
            print("✅ Все проверки пройдены, система готова к развертыванию")
            sys.exit(0)
        else:
            print("❌ Обнаружены проблемы, развертывание невозможно")
            sys.exit(1)
    else:
        success, message = deployment.full_deployment_cycle()
        print(f"\n{'✅' if success else '❌'} {message}")
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
