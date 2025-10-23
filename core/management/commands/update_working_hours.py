from django.core.management.base import BaseCommand
from core.models import Specialist


class Command(BaseCommand):
    help = 'Обновляет рабочие часы специалистов'

    def handle(self, *args, **options):
        self.stdout.write('Обновление рабочих часов специалистов...')

        # Унифицированные рабочие часы для всех специалистов
        # Вс, Пн, Вт, Ср, Чт: 10:00-19:00; Пт, Сб: выходные
        working_hours_unified = {
            'monday': {'start': '10:00', 'end': '19:00'},
            'tuesday': {'start': '10:00', 'end': '19:00'},
            'wednesday': {'start': '10:00', 'end': '19:00'},
            'thursday': {'start': '10:00', 'end': '19:00'},
            'sunday': {'start': '10:00', 'end': '19:00'}
        }

        # Обновляем рабочие часы для всех специалистов
        specialists_data = [
            {'name': 'Екатерина', 'working_hours': working_hours_unified},
            {'name': 'Римма', 'working_hours': working_hours_unified},
            {'name': 'Авраам', 'working_hours': working_hours_unified}
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
