from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Сбрасывает пароль для admin пользователя'

    def add_arguments(self, parser):
        parser.add_argument(
            '--password',
            type=str,
            default='admin123',
            help='Новый пароль для admin пользователя'
        )

    def handle(self, *args, **options):
        password = options['password']
        
        try:
            admin_user = User.objects.get(username='admin')
            admin_user.set_password(password)
            admin_user.is_superuser = True
            admin_user.is_staff = True
            admin_user.is_active = True
            admin_user.save()
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ Пароль для admin пользователя сброшен: {password}')
            )
            self.stdout.write(f'Логин: admin')
            self.stdout.write(f'Пароль: {password}')
            
        except User.DoesNotExist:
            # Создаем admin пользователя если его нет
            admin_user = User.objects.create_user(
                username='admin',
                email='admin@example.com',
                password=password
            )
            admin_user.is_superuser = True
            admin_user.is_staff = True
            admin_user.is_active = True
            admin_user.save()
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ Admin пользователь создан с паролем: {password}')
            )
