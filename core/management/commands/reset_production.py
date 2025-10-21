from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from datetime import datetime, timedelta
from core.models import Patient, Service, Specialist, Appointment, DialogLog, FAQ, ContactMessage


class Command(BaseCommand):
    help = 'Полная очистка базы данных и создание только реальных данных согласно SmartSecretary.md'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Подтверждение выполнения команды (обязательно)',
        )
        parser.add_argument(
            '--keep-superuser',
            action='store_true',
            help='Сохранить суперпользователей',
        )

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(
                self.style.ERROR(
                    'ВНИМАНИЕ! Эта команда полностью очистит базу данных!\n'
                    'Для выполнения добавьте флаг --confirm'
                )
            )
            return

        self.stdout.write(
            self.style.WARNING(
                'Начинаю полную очистку базы данных и создание реальных данных...'
            )
        )

        try:
            with transaction.atomic():
                # 1. Очистка всех данных
                self.clear_all_data()
                
                # 2. Создание реальных специалистов
                specialists = self.create_specialists()
                
                # 3. Создание реальных услуг
                services = self.create_services()
                
                # 4. Создание демонстрационных пациентов
                patients = self.create_demo_patients()
                
                # 5. Создание нескольких демонстрационных записей
                self.create_demo_appointments(specialists, services, patients)

            self.stdout.write(
                self.style.SUCCESS(
                    'База данных успешно очищена и заполнена реальными данными!'
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Ошибка при выполнении команды: {e}')
            )
            raise

    def clear_all_data(self):
        """Очистка всех данных"""
        self.stdout.write('Очищаю базу данных...')
        
        # Удаляем в правильном порядке (учитывая внешние ключи)
        Appointment.objects.all().delete()
        DialogLog.objects.all().delete()
        ContactMessage.objects.all().delete()
        FAQ.objects.all().delete()
        Patient.objects.all().delete()
        Service.objects.all().delete()
        Specialist.objects.all().delete()
        
        self.stdout.write(self.style.SUCCESS('✓ База данных очищена'))

    def create_specialists(self):
        """Создание реальных специалистов согласно SmartSecretary.md"""
        self.stdout.write('Создаю специалистов...')
        
        specialists_data = [
            {
                'name': 'Екатерина',
                'specialty': 'Врач-реабилитолог, врач спортивной медицины, остеопат',
                'description': '''Стаж работы с 2010 года.
Основные направления: травмы и заболевания ОДА, восстановление после операций, реабилитация спортсменов, заболевания позвоночника, онкореабилитация, реабилитация во время беременности и после родов, детская реабилитация (включая РАС и ДЦП).

Применяемые методы:
• Остеопатия
• Мануальная терапия и прикладная кинезиология  
• Лечебный массаж (спортивный, баночный, детский)
• Аппаратная физиотерапия
• Exercise physiotherapy
• Кинезиотейпирование''',
                'is_active': True
            },
            {
                'name': 'Римма',
                'specialty': 'Врач педиатр, врач нутрициолог',
                'description': '''Кандидат медицинских наук. Опыт работы 40 лет.
Обладает глубокими знаниями в области детского и взрослого здоровья, питания и доказательной медицины.

Специализация:
• Комплексная оценка здоровья детей и взрослых
• Разработка индивидуальных планов питания
• Профилактика и лечение заболеваний, связанных с питанием
• Применение научных знаний в практической медицине''',
                'is_active': True
            },
            {
                'name': 'Авраам',
                'specialty': 'Массажист',
                'description': '''Применяемые методы:
• Мануальная терапия в вертебрологии
• Лечебный массаж: классический шведский, акупрессура и точечный массаж, спортивный массаж, детский, лечебный (при заболеваниях нервной системы, легочной системы)
• Акупунктура
• Вакуумные банки
• Кинезиотейпирование

Специализация на работе с мужчинами и парнями-подростками.''',
                'is_active': True
            }
        ]
        
        specialists = []
        for data in specialists_data:
            specialist = Specialist.objects.create(**data)
            specialists.append(specialist)
            self.stdout.write(f'✓ Создан специалист: {specialist.name}')
        
        return specialists

    def create_services(self):
        """Создание реальных услуг с точными ценами из каталога"""
        self.stdout.write('Создаю услуги...')
        
        services_data = [
            # Консультации
            {
                'name': 'Консультация реабилитолога',
                'description': 'Включает комплексное обследование пациента, сбор анамнеза, физический осмотр, оценку двигательных функций и разработку индивидуальной программы реабилитации.',
                'price': 80,
                'currency': '₪',
                'duration': 20,
                'catalog': 'A',
                'is_active': True
            },
            {
                'name': 'Консультация нутрициолога',
                'description': 'Включает первичный сбор информации, анализ данных, разработку индивидуального плана питания и поддержку.',
                'price': 450,
                'currency': '₪',
                'duration': 50,
                'catalog': 'A',
                'is_active': True
            },
            {
                'name': 'Консультация остеопата',
                'description': 'Включает сбор анамнеза, диагностику и план лечения с использованием остеопатических техник.',
                'price': 80,
                'currency': '₪',
                'duration': 20,
                'catalog': 'A',
                'is_active': True
            },
            
            # Массаж для мужчин
            {
                'name': 'Лечебный массаж (мужчины) - классический шведский',
                'description': 'Классический шведский массаж для мужчин и парней-подростков.',
                'price': 250,
                'currency': '₪',
                'duration': 55,
                'catalog': 'A',
                'is_active': True
            },
            {
                'name': 'Лечебный массаж (мужчины) - спортивный',
                'description': 'Спортивный массаж для мужчин и парней-подростков.',
                'price': 250,
                'currency': '₪',
                'duration': 55,
                'catalog': 'A',
                'is_active': True
            },
            {
                'name': 'Лечебный массаж (мужчины) - лечебный',
                'description': 'Лечебный массаж при заболеваниях нервной системы, легочной системы для мужчин.',
                'price': 250,
                'currency': '₪',
                'duration': 55,
                'catalog': 'A',
                'is_active': True
            },
            
            # Массаж для женщин и детей
            {
                'name': 'Лечебный массаж (женщины) - классический шведский',
                'description': 'Классический шведский массаж для женщин и девушек-подростков.',
                'price': 250,
                'currency': '₪',
                'duration': 55,
                'catalog': 'A',
                'is_active': True
            },
            {
                'name': 'Детский массаж',
                'description': 'Лечебный массаж для детей.',
                'price': 150,
                'currency': '₪',
                'duration': 45,
                'catalog': 'A',
                'is_active': True
            },
            {
                'name': 'Массаж для грудных детей',
                'description': 'Специальный массаж для грудных детей.',
                'price': 70,
                'currency': '₪',
                'duration': 25,
                'catalog': 'A',
                'is_active': True
            },
            {
                'name': 'Массаж для беременных',
                'description': 'Лечебный массаж для беременных от 5 месяцев.',
                'price': 180,
                'currency': '₪',
                'duration': 35,
                'catalog': 'A',
                'is_active': True
            },
            
            # Дополнительные услуги
            {
                'name': 'Кинезиотейпирование',
                'description': 'Применяется для профилактики и реабилитации травм мышц, связок и суставов.',
                'price': 50,
                'currency': '₪',
                'duration': 15,
                'catalog': 'A',
                'is_active': True
            },
            {
                'name': 'Подбор и демонстрация комплекса упражнений',
                'description': 'Индивидуальный подбор упражнений для реабилитации после травм, после родов и др.',
                'price': 100,
                'currency': '₪',
                'duration': 30,
                'catalog': 'A',
                'is_active': True
            },
            
            # Диагностика
            {
                'name': 'Диагностика биорезонансным сканированием (базовая)',
                'description': 'Полная распечатка результата без эпикриза.',
                'price': 300,
                'currency': '₪',
                'duration': 30,
                'catalog': 'A',
                'is_active': True
            },
            {
                'name': 'Диагностика биорезонансным сканированием (расширенная)',
                'description': 'Выявление проблем, эпикриз и рекомендации.',
                'price': 750,
                'currency': '₪',
                'duration': 60,
                'catalog': 'A',
                'is_active': True
            },
            {
                'name': 'Диагностика биорезонансным сканированием (VIP)',
                'description': 'Полный пакет: выявление проблем, эпикриз, рекомендации, индивидуальный комплекс упражнений, массажи и иглотерапия, сопровождение по WhatsApp.',
                'price': 5500,
                'currency': '₪',
                'duration': 120,
                'catalog': 'A',
                'is_active': True
            }
        ]
        
        services = []
        for data in services_data:
            service = Service.objects.create(**data)
            services.append(service)
            self.stdout.write(f'✓ Создана услуга: {service.name} - {service.price}{service.currency}')
        
        return services

    def create_demo_patients(self):
        """Создание демонстрационных пациентов с реальными данными"""
        self.stdout.write('Создаю демонстрационных пациентов...')
        
        patients_data = [
            {
                'name': 'Александр Петров',
                'phone': '+972541234567',
                'email': 'alex.petrov@example.com',
                'country': 'Israel',
                'city': 'Иерусалим'
            },
            {
                'name': 'Мария Иванова',
                'phone': '+79161234567',
                'email': 'maria.ivanova@example.com',
                'country': 'Russia',
                'city': 'Москва'
            },
            {
                'name': 'Екатерина Сидорова',
                'phone': '+380671234567',
                'email': 'kate.sidorova@example.com',
                'country': 'Ukraine',
                'city': 'Киев'
            },
            {
                'name': 'David Johnson',
                'phone': '+12125551234',
                'email': 'david.johnson@example.com',
                'country': 'USA',
                'city': 'New York'
            },
            {
                'name': 'Sarah Cohen',
                'phone': '+972521234567',
                'email': 'sarah.cohen@example.com',
                'country': 'Israel',
                'city': 'Тель-Авив'
            },
            {
                'name': 'Анна Козлова',
                'phone': '+79261234567',
                'email': 'anna.kozlova@example.com',
                'country': 'Russia',
                'city': 'Санкт-Петербург'
            }
        ]
        
        patients = []
        for data in patients_data:
            patient = Patient.objects.create(**data)
            patients.append(patient)
            self.stdout.write(f'✓ Создан пациент: {patient.name} ({patient.country})')
        
        return patients

    def create_demo_appointments(self, specialists, services, patients):
        """Создание демонстрационных записей"""
        self.stdout.write('Создаю демонстрационные записи...')
        
        # Создаем несколько записей на ближайшие дни
        base_date = timezone.now().date()
        
        appointments_data = [
            {
                'patient': patients[0],  # Александр Петров
                'specialist': specialists[2],  # Авраам (массажист для мужчин)
                'service': services[3],  # Лечебный массаж (мужчины)
                'start_time': timezone.make_aware(datetime.combine(base_date + timedelta(days=1), datetime.strptime('10:00', '%H:%M').time())),
                'status': 'confirmed',
                'channel': 'web'
            },
            {
                'patient': patients[1],  # Мария Иванова
                'specialist': specialists[1],  # Римма (нутрициолог)
                'service': services[1],  # Консультация нутрициолога
                'start_time': timezone.make_aware(datetime.combine(base_date + timedelta(days=2), datetime.strptime('15:00', '%H:%M').time())),
                'status': 'pending',
                'channel': 'phone'
            },
            {
                'patient': patients[2],  # Екатерина Сидорова
                'specialist': specialists[0],  # Екатерина (реабилитолог)
                'service': services[0],  # Консультация реабилитолога
                'start_time': timezone.make_aware(datetime.combine(base_date + timedelta(days=3), datetime.strptime('11:30', '%H:%M').time())),
                'status': 'confirmed',
                'channel': 'whatsapp'
            },
            {
                'patient': patients[4],  # Sarah Cohen
                'specialist': specialists[0],  # Екатерина (остеопат)
                'service': services[13],  # Диагностика расширенная
                'start_time': timezone.make_aware(datetime.combine(base_date + timedelta(days=4), datetime.strptime('16:00', '%H:%M').time())),
                'status': 'pending',
                'channel': 'web'
            }
        ]
        
        for data in appointments_data:
            # Вычисляем время окончания
            duration = data['service'].duration
            end_time = data['start_time'] + timedelta(minutes=duration)
            data['end_time'] = end_time
            
            appointment = Appointment.objects.create(**data)
            self.stdout.write(
                f'✓ Создана запись: {appointment.patient.name} → {appointment.specialist.name} '
                f'({appointment.start_time.strftime("%d.%m.%Y %H:%M")})'
            )

        self.stdout.write(self.style.SUCCESS(f'Создано {len(appointments_data)} демонстрационных записей'))
