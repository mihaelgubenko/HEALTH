from django.core.management.base import BaseCommand
from core.models import Specialist


class Command(BaseCommand):
    help = 'Обновляет рабочие часы специалистов'

    def handle(self, *args, **options):
        self.stdout.write('Обновление рабочих часов специалистов...')

        # Новые рабочие часы (без пятницы)
        working_hours_ekaterina = {
            'monday': {'start': '09:00', 'end': '19:00'},
            'tuesday': {'start': '09:00', 'end': '19:00'},
            'wednesday': {'start': '09:00', 'end': '19:00'},
            'thursday': {'start': '09:00', 'end': '19:00'},
            'saturday': {'start': '09:00', 'end': '14:00'},
            'sunday': {'start': '10:00', 'end': '16:00'}
        }

        working_hours_rimma = {
            'monday': {'start': '10:00', 'end': '18:00'},
            'tuesday': {'start': '10:00', 'end': '18:00'},
            'wednesday': {'start': '10:00', 'end': '18:00'},
            'thursday': {'start': '10:00', 'end': '18:00'},
            'saturday': {'start': '10:00', 'end': '14:00'},
            'sunday': {'start': '10:00', 'end': '14:00'}
        }

        working_hours_avraam = {
            'monday': {'start': '09:00', 'end': '19:00'},
            'tuesday': {'start': '09:00', 'end': '19:00'},
            'wednesday': {'start': '09:00', 'end': '19:00'},
            'thursday': {'start': '09:00', 'end': '19:00'},
            'saturday': {'start': '09:00', 'end': '14:00'},
            'sunday': {'start': '10:00', 'end': '16:00'}
        }

        # Обновляем рабочие часы
        specialists_data = [
            {'name': 'Екатерина', 'working_hours': working_hours_ekaterina},
            {'name': 'Римма', 'working_hours': working_hours_rimma},
            {'name': 'Авраам', 'working_hours': working_hours_avraam}
        ]

        updated_count = 0
        for data in specialists_data:
            try:
                specialist = Specialist.objects.get(name=data['name'])
                specialist.working_hours = data['working_hours']
                specialist.save()
                self.stdout.write(f'Обновлены рабочие часы для {specialist.name}')
                updated_count += 1
            except Specialist.DoesNotExist:
                self.stdout.write(f'Специалист {data["name"]} не найден')

        self.stdout.write(f'\nОбновлено {updated_count} специалистов')
        self.stdout.write(
            self.style.SUCCESS('✅ Рабочие часы успешно обновлены!')
        )
