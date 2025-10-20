from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from core.models import Service, Specialist, Patient, Appointment, DialogLog
from core.lite_secretary import LiteSmartSecretary
import openai
from datetime import timedelta

class Command(BaseCommand):
    help = 'Проверка здоровья системы ИИ-секретаря'

    def add_arguments(self, parser):
        parser.add_argument(
            '--full',
            action='store_true',
            help='Полная проверка включая тест ИИ',
        )

    def handle(self, *args, **options):
        self.stdout.write('🔍 Проверка здоровья системы ИИ-секретаря...\n')
        
        total_checks = 0
        passed_checks = 0
        
        # 1. Проверка базы данных
        total_checks += 1
        try:
            services_count = Service.objects.count()
            specialists_count = Specialist.objects.count()
            patients_count = Patient.objects.count()
            
            self.stdout.write(f'✅ База данных: {services_count} услуг, {specialists_count} специалистов, {patients_count} пациентов')
            passed_checks += 1
        except Exception as e:
            self.stdout.write(f'❌ База данных: {e}')
        
        # 2. Проверка OpenAI API
        total_checks += 1
        try:
            if settings.OPENAI_API_KEY:
                client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
                # Простой тест
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": "test"}],
                    max_tokens=5,
                    timeout=5
                )
                self.stdout.write('✅ OpenAI API: подключение работает')
                passed_checks += 1
            else:
                self.stdout.write('❌ OpenAI API: ключ не настроен')
        except Exception as e:
            self.stdout.write(f'❌ OpenAI API: {e}')
        
        # 3. Проверка ИИ-секретаря
        if options['full']:
            total_checks += 1
            try:
                secretary = LiteSmartSecretary()
                test_response = secretary.process_message("тест", "health_check_session")
                
                if 'reply' in test_response:
                    self.stdout.write('✅ ИИ-секретарь: отвечает на сообщения')
                    passed_checks += 1
                else:
                    self.stdout.write('❌ ИИ-секретарь: неверный формат ответа')
            except Exception as e:
                self.stdout.write(f'❌ ИИ-секретарь: {e}')
        
        # 4. Проверка активности за последние 24 часа
        total_checks += 1
        try:
            yesterday = timezone.now() - timedelta(hours=24)
            recent_dialogs = DialogLog.objects.filter(created_at__gte=yesterday).count()
            recent_appointments = Appointment.objects.filter(created_at__gte=yesterday).count()
            
            self.stdout.write(f'✅ Активность (24ч): {recent_dialogs} диалогов, {recent_appointments} записей')
            passed_checks += 1
        except Exception as e:
            self.stdout.write(f'❌ Активность: {e}')
        
        # 5. Проверка будущих записей
        total_checks += 1
        try:
            future_appointments = Appointment.objects.filter(
                start_time__gt=timezone.now(),
                status__in=['pending', 'confirmed']
            ).count()
            
            self.stdout.write(f'✅ Будущие записи: {future_appointments} шт.')
            passed_checks += 1
        except Exception as e:
            self.stdout.write(f'❌ Будущие записи: {e}')
        
        # Итоговый результат
        health_percentage = (passed_checks / total_checks) * 100
        
        self.stdout.write('\n' + '='*50)
        self.stdout.write(f'🏥 ЗДОРОВЬЕ СИСТЕМЫ: {passed_checks}/{total_checks} ({health_percentage:.1f}%)')
        
        if health_percentage >= 80:
            self.stdout.write('🟢 Система работает отлично!')
        elif health_percentage >= 60:
            self.stdout.write('🟡 Система работает с небольшими проблемами')
        else:
            self.stdout.write('🔴 Система требует внимания!')
        
        self.stdout.write('='*50)
        
        # Рекомендации
        if passed_checks < total_checks:
            self.stdout.write('\n📋 РЕКОМЕНДАЦИИ:')
            
            if not settings.OPENAI_API_KEY:
                self.stdout.write('• Настройте OPENAI_API_KEY в .env файле')
            
            if recent_dialogs == 0:
                self.stdout.write('• Нет активности - проверьте чат на сайте')
            
            self.stdout.write('• Проверьте логи Django для деталей ошибок')
            
        return f"Health check completed: {health_percentage:.1f}%"
