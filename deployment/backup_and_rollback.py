#!/usr/bin/env python
"""
Система безопасного развертывания и отката для проекта HEALTH
Создает полные бэкапы перед внедрением изменений и позволяет быстро откатиться
"""

import os
import sys
import json
import shutil
import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Добавляем путь к Django проекту
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_secretary.settings')

import django
django.setup()

from django.conf import settings
from django.core.management import call_command
from django.db import connection


class BackupAndRollback:
    """Система бэкапа и отката для безопасного развертывания"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.backup_dir = self.project_root / 'backups'
        self.backup_dir.mkdir(exist_ok=True)
        
        # Критические файлы для бэкапа
        self.critical_files = [
            'core/validators.py',
            'core/forms.py', 
            'core/models.py',
            'core/admin.py',
            'core/views.py',
            'core/lite_secretary.py',
            'smart_secretary/settings.py',
            'requirements.txt'
        ]
        
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.backup_name = f"backup_{self.timestamp}"
        self.backup_path = self.backup_dir / self.backup_name
        
    def create_full_backup(self) -> Tuple[bool, str]:
        """Создает полный бэкап системы"""
        try:
            print(f"🔄 Создание полного бэкапа: {self.backup_name}")
            
            # Создаем директорию бэкапа
            self.backup_path.mkdir(exist_ok=True)
            
            # 1. Бэкап базы данных
            db_backup_success, db_message = self._backup_database()
            if not db_backup_success:
                return False, f"Ошибка бэкапа БД: {db_message}"
            
            # 2. Бэкап критических файлов
            files_backup_success, files_message = self._backup_files()
            if not files_backup_success:
                return False, f"Ошибка бэкапа файлов: {files_message}"
            
            # 3. Бэкап конфигурации
            config_backup_success, config_message = self._backup_configuration()
            if not config_backup_success:
                return False, f"Ошибка бэкапа конфигурации: {config_message}"
            
            # 4. Создание манифеста бэкапа
            manifest_success, manifest_message = self._create_backup_manifest()
            if not manifest_success:
                return False, f"Ошибка создания манифеста: {manifest_message}"
            
            print(f"✅ Полный бэкап создан успешно: {self.backup_path}")
            return True, f"Бэкап создан: {self.backup_name}"
            
        except Exception as e:
            return False, f"Критическая ошибка при создании бэкапа: {str(e)}"
    
    def _backup_database(self) -> Tuple[bool, str]:
        """Создает бэкап базы данных"""
        try:
            db_backup_path = self.backup_path / 'database'
            db_backup_path.mkdir(exist_ok=True)
            
            # Для SQLite
            if 'sqlite' in settings.DATABASES['default']['ENGINE']:
                db_path = settings.DATABASES['default']['NAME']
                if os.path.exists(db_path):
                    shutil.copy2(db_path, db_backup_path / 'db.sqlite3')
                    print("  📁 SQLite база данных скопирована")
            
            # Для PostgreSQL (Railway)
            elif 'postgresql' in settings.DATABASES['default']['ENGINE']:
                # Создаем дамп через Django
                dump_path = db_backup_path / 'db_dump.json'
                with open(dump_path, 'w', encoding='utf-8') as f:
                    call_command('dumpdata', stdout=f, indent=2)
                print("  📁 PostgreSQL дамп создан")
            
            # Дополнительно создаем JSON дамп всех данных
            json_dump_path = db_backup_path / 'full_data_dump.json'
            with open(json_dump_path, 'w', encoding='utf-8') as f:
                call_command('dumpdata', stdout=f, indent=2, 
                           exclude=['contenttypes', 'auth.permission'])
            
            return True, "База данных сохранена"
            
        except Exception as e:
            return False, str(e)
    
    def _backup_files(self) -> Tuple[bool, str]:
        """Создает бэкап критических файлов"""
        try:
            files_backup_path = self.backup_path / 'files'
            files_backup_path.mkdir(exist_ok=True)
            
            backed_up_files = []
            
            for file_path in self.critical_files:
                source_path = self.project_root / file_path
                if source_path.exists():
                    # Создаем структуру директорий
                    dest_path = files_backup_path / file_path
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Копируем файл
                    shutil.copy2(source_path, dest_path)
                    backed_up_files.append(file_path)
            
            print(f"  📁 Скопировано файлов: {len(backed_up_files)}")
            return True, f"Скопировано {len(backed_up_files)} файлов"
            
        except Exception as e:
            return False, str(e)
    
    def _backup_configuration(self) -> Tuple[bool, str]:
        """Создает бэкап конфигурации"""
        try:
            config_backup_path = self.backup_path / 'config'
            config_backup_path.mkdir(exist_ok=True)
            
            # Сохраняем текущие настройки Django
            config = {
                'DEBUG': settings.DEBUG,
                'ALLOWED_HOSTS': settings.ALLOWED_HOSTS,
                'TIME_ZONE': settings.TIME_ZONE,
                'USE_TZ': settings.USE_TZ,
                'DATABASES': {
                    'ENGINE': settings.DATABASES['default']['ENGINE'],
                    'NAME': settings.DATABASES['default']['NAME']
                },
                'INSTALLED_APPS': settings.INSTALLED_APPS,
                'MIDDLEWARE': settings.MIDDLEWARE,
            }
            
            config_file = config_backup_path / 'django_settings.json'
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, default=str)
            
            # Сохраняем переменные окружения
            env_vars = {
                'DJANGO_SETTINGS_MODULE': os.environ.get('DJANGO_SETTINGS_MODULE'),
                'DATABASE_URL': os.environ.get('DATABASE_URL', ''),
                'SECRET_KEY': os.environ.get('SECRET_KEY', ''),
            }
            
            env_file = config_backup_path / 'environment.json'
            with open(env_file, 'w', encoding='utf-8') as f:
                json.dump(env_vars, f, indent=2)
            
            print("  📁 Конфигурация сохранена")
            return True, "Конфигурация сохранена"
            
        except Exception as e:
            return False, str(e)
    
    def _create_backup_manifest(self) -> Tuple[bool, str]:
        """Создает манифест бэкапа с метаданными"""
        try:
            manifest = {
                'backup_name': self.backup_name,
                'timestamp': self.timestamp,
                'created_at': datetime.now().isoformat(),
                'project_root': str(self.project_root),
                'python_version': sys.version,
                'django_version': django.get_version(),
                'critical_files': self.critical_files,
                'backup_type': 'full',
                'description': 'Полный бэкап перед внедрением системы валидации',
                'rollback_instructions': [
                    '1. Остановить сервер',
                    '2. Восстановить файлы из backup/files/',
                    '3. Восстановить базу данных из backup/database/',
                    '4. Перезапустить сервер',
                    '5. Проверить работоспособность'
                ]
            }
            
            manifest_file = self.backup_path / 'manifest.json'
            with open(manifest_file, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2, ensure_ascii=False)
            
            print("  📁 Манифест создан")
            return True, "Манифест создан"
            
        except Exception as e:
            return False, str(e)
    
    def list_backups(self) -> List[Dict]:
        """Возвращает список всех доступных бэкапов"""
        backups = []
        
        for backup_dir in self.backup_dir.glob('backup_*'):
            if backup_dir.is_dir():
                manifest_file = backup_dir / 'manifest.json'
                if manifest_file.exists():
                    try:
                        with open(manifest_file, 'r', encoding='utf-8') as f:
                            manifest = json.load(f)
                        backups.append({
                            'name': manifest['backup_name'],
                            'created_at': manifest['created_at'],
                            'description': manifest.get('description', ''),
                            'path': str(backup_dir)
                        })
                    except:
                        # Если манифест поврежден, добавляем базовую информацию
                        backups.append({
                            'name': backup_dir.name,
                            'created_at': 'unknown',
                            'description': 'Поврежденный манифест',
                            'path': str(backup_dir)
                        })
        
        return sorted(backups, key=lambda x: x['created_at'], reverse=True)
    
    def rollback_from_backup(self, backup_name: str) -> Tuple[bool, str]:
        """Выполняет откат из указанного бэкапа"""
        try:
            backup_path = self.backup_dir / backup_name
            if not backup_path.exists():
                return False, f"Бэкап {backup_name} не найден"
            
            print(f"🔄 Начинаем откат из бэкапа: {backup_name}")
            
            # 1. Восстанавливаем файлы
            files_success, files_message = self._restore_files(backup_path)
            if not files_success:
                return False, f"Ошибка восстановления файлов: {files_message}"
            
            # 2. Восстанавливаем базу данных
            db_success, db_message = self._restore_database(backup_path)
            if not db_success:
                return False, f"Ошибка восстановления БД: {db_message}"
            
            print(f"✅ Откат из бэкапа {backup_name} выполнен успешно")
            return True, f"Система восстановлена из бэкапа {backup_name}"
            
        except Exception as e:
            return False, f"Критическая ошибка при откате: {str(e)}"
    
    def _restore_files(self, backup_path: Path) -> Tuple[bool, str]:
        """Восстанавливает файлы из бэкапа"""
        try:
            files_backup_path = backup_path / 'files'
            if not files_backup_path.exists():
                return False, "Директория с файлами не найдена в бэкапе"
            
            restored_files = []
            
            for file_path in self.critical_files:
                backup_file = files_backup_path / file_path
                if backup_file.exists():
                    target_file = self.project_root / file_path
                    
                    # Создаем директорию если нужно
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Восстанавливаем файл
                    shutil.copy2(backup_file, target_file)
                    restored_files.append(file_path)
            
            print(f"  📁 Восстановлено файлов: {len(restored_files)}")
            return True, f"Восстановлено {len(restored_files)} файлов"
            
        except Exception as e:
            return False, str(e)
    
    def _restore_database(self, backup_path: Path) -> Tuple[bool, str]:
        """Восстанавливает базу данных из бэкапа"""
        try:
            db_backup_path = backup_path / 'database'
            if not db_backup_path.exists():
                return False, "Директория с БД не найдена в бэкапе"
            
            # Для SQLite
            if 'sqlite' in settings.DATABASES['default']['ENGINE']:
                backup_db = db_backup_path / 'db.sqlite3'
                if backup_db.exists():
                    target_db = settings.DATABASES['default']['NAME']
                    shutil.copy2(backup_db, target_db)
                    print("  📁 SQLite база данных восстановлена")
            
            # Для PostgreSQL - восстанавливаем из JSON дампа
            json_dump = db_backup_path / 'full_data_dump.json'
            if json_dump.exists():
                # Очищаем текущие данные (осторожно!)
                call_command('flush', '--noinput')
                # Загружаем данные из дампа
                call_command('loaddata', str(json_dump))
                print("  📁 Данные восстановлены из JSON дампа")
            
            return True, "База данных восстановлена"
            
        except Exception as e:
            return False, str(e)
    
    def quick_rollback(self) -> Tuple[bool, str]:
        """Быстрый откат к последнему бэкапу"""
        backups = self.list_backups()
        if not backups:
            return False, "Нет доступных бэкапов для отката"
        
        latest_backup = backups[0]
        return self.rollback_from_backup(latest_backup['name'])
    
    def health_check(self) -> Dict[str, bool]:
        """Проверка работоспособности системы после изменений"""
        checks = {}
        
        try:
            # Проверка подключения к БД
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                checks['database'] = True
        except:
            checks['database'] = False
        
        try:
            # Проверка импорта критических модулей
            from core.models import Patient, Appointment, Service, Specialist
            from core.validators import ValidationManager
            from core.forms import AppointmentForm
            checks['imports'] = True
        except:
            checks['imports'] = False
        
        try:
            # Проверка создания записи (тест)
            from core.models import Patient
            test_patient = Patient.objects.filter(phone='+972000000000').first()
            checks['models'] = True
        except:
            checks['models'] = False
        
        return checks


def main():
    """Главная функция для запуска из командной строки"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Система бэкапа и отката')
    parser.add_argument('action', choices=['backup', 'rollback', 'list', 'health'], 
                       help='Действие для выполнения')
    parser.add_argument('--backup-name', help='Имя бэкапа для отката')
    
    args = parser.parse_args()
    
    backup_system = BackupAndRollback()
    
    if args.action == 'backup':
        success, message = backup_system.create_full_backup()
        print(f"{'✅' if success else '❌'} {message}")
        sys.exit(0 if success else 1)
    
    elif args.action == 'rollback':
        if args.backup_name:
            success, message = backup_system.rollback_from_backup(args.backup_name)
        else:
            success, message = backup_system.quick_rollback()
        print(f"{'✅' if success else '❌'} {message}")
        sys.exit(0 if success else 1)
    
    elif args.action == 'list':
        backups = backup_system.list_backups()
        if backups:
            print("📋 Доступные бэкапы:")
            for backup in backups:
                print(f"  • {backup['name']} - {backup['created_at']}")
                print(f"    {backup['description']}")
        else:
            print("📋 Бэкапы не найдены")
    
    elif args.action == 'health':
        checks = backup_system.health_check()
        print("🏥 Проверка работоспособности:")
        for check, status in checks.items():
            print(f"  {'✅' if status else '❌'} {check}")
        
        all_good = all(checks.values())
        sys.exit(0 if all_good else 1)


if __name__ == '__main__':
    main()
