from django.core.management.base import BaseCommand
from django.core.management import call_command
from core.models import Service, Specialist, FAQ, Patient, Appointment


class Command(BaseCommand):
    help = 'Полная очистка базы данных и создание тестовых данных'

    def handle(self, *args, **options):
        self.stdout.write('🧹 Полная очистка базы данных...')

        # Удаляем все данные
        Appointment.objects.all().delete()
        Patient.objects.all().delete()
        FAQ.objects.all().delete()
        Service.objects.all().delete()
        Specialist.objects.all().delete()

        self.stdout.write('✅ База данных очищена')

        # Загружаем начальные данные
        self.stdout.write('📥 Загрузка тестовых данных...')
        call_command('load_initial_data')

        self.stdout.write(
            self.style.SUCCESS('🎉 База данных успешно сброшена и заполнена тестовыми данными!')
        )
