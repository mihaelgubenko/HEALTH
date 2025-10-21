from django.core.management.base import BaseCommand
from django.db.models import Q
from core.models import Patient, Service, Specialist, Appointment, ContactMessage


class Command(BaseCommand):
    help = 'Очистка тестовых данных в продакшен базе данных'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Подтвердить удаление тестовых данных',
        )

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(
                self.style.WARNING(
                    'Для выполнения очистки добавьте --confirm\n'
                    'python manage.py cleanup_production --confirm'
                )
            )
            return

        self.stdout.write('🧹 Начинаем очистку тестовых данных...')
        
        # Список тестовых ключевых слов
        test_keywords = [
            'тест', 'test', 'граничн', 'стресс', 'форма', 'debug', 'sample',
            'example', 'demo', 'временн', 'temp', 'tmp', 'fake', 'dummy',
            'нагрузочн', 'тестов', 'специальност', 'тестирован'
        ]
        
        def is_test_data(text):
            if not text:
                return False
            text_lower = text.lower()
            return any(keyword in text_lower for keyword in test_keywords)

        # 1. Очистка специалистов
        self.stdout.write('\n👨‍⚕️ Очистка тестовых специалистов:')
        test_specialists = []
        
        for specialist in Specialist.objects.all():
            if (is_test_data(specialist.name) or 
                is_test_data(specialist.specialty) or
                specialist.name in ['Стресс Специалист', 'Тест Специалист', 
                                   'Тестовый Специалист', 'Форма Специалист', 
                                   'Граничный Специалист']):
                test_specialists.append(specialist)
        
        for specialist in test_specialists:
            appointments_count = specialist.appointment_set.count()
            self.stdout.write(f'  Удаляем: {specialist.name} ({appointments_count} записей)')
            specialist.appointment_set.all().delete()
            specialist.delete()

        # 2. Очистка услуг
        self.stdout.write('\n🏥 Очистка тестовых услуг:')
        test_services = []
        
        for service in Service.objects.all():
            if (is_test_data(service.name) or
                service.name in ['Тест Услуга', 'Тестовая Услуга', 'Стресс Услуга', 
                               'Форма Услуга', 'Граничная Услуга']):
                test_services.append(service)
        
        for service in test_services:
            appointments_count = service.appointment_set.count()
            self.stdout.write(f'  Удаляем: {service.name} ({appointments_count} записей)')
            service.appointment_set.all().delete()
            service.delete()

        # 3. Очистка пациентов
        self.stdout.write('\n👥 Очистка тестовых пациентов:')
        test_patients = []
        
        for patient in Patient.objects.all():
            if (is_test_data(patient.name) or 
                is_test_data(patient.phone) or
                patient.name.startswith('Стресс Пациент') or
                patient.name.startswith('Тест ') or
                'тест' in patient.name.lower()):
                test_patients.append(patient)
        
        for patient in test_patients:
            appointments_count = patient.appointment_set.count()
            self.stdout.write(f'  Удаляем: {patient.name} ({appointments_count} записей)')
            patient.appointment_set.all().delete()
            patient.delete()

        # 4. Статистика
        self.stdout.write('\n📊 Финальная статистика:')
        self.stdout.write(f'  Пациенты: {Patient.objects.count()}')
        self.stdout.write(f'  Услуги: {Service.objects.count()}')
        self.stdout.write(f'  Специалисты: {Specialist.objects.count()}')
        self.stdout.write(f'  Записи: {Appointment.objects.count()}')
        
        self.stdout.write('\n👨‍⚕️ Оставшиеся специалисты:')
        for specialist in Specialist.objects.all():
            self.stdout.write(f'  - {specialist.name} ({specialist.specialty})')
        
        self.stdout.write(
            self.style.SUCCESS('\n✅ Очистка завершена!')
        )
