"""
Аналитика работы ИИ-секретаря
"""
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta, datetime
from .models import DialogLog, Appointment

class SecretaryAnalytics:
    """Аналитика работы ИИ-секретаря"""
    
    def get_daily_stats(self, date=None):
        """Статистика за день"""
        if not date:
            date = timezone.now().date()
        
        # Диалоги за день
        dialogs = DialogLog.objects.filter(
            created_at__date=date
        )
        
        # Записи, созданные через ИИ
        appointments = Appointment.objects.filter(
            created_at__date=date,
            channel='web'
        )
        
        # Анализ намерений
        intents = dialogs.values('intent').annotate(
            count=Count('intent')
        ).order_by('-count')
        
        return {
            'date': date.strftime('%d.%m.%Y'),
            'total_dialogs': dialogs.count(),
            'unique_sessions': dialogs.values('session_id').distinct().count(),
            'appointments_created': appointments.count(),
            'top_intents': list(intents[:5]),
            'conversion_rate': round(
                (appointments.count() / max(dialogs.count(), 1)) * 100, 2
            )
        }
    
    def get_success_rate(self, days=7):
        """Показатель успешности диалогов"""
        since_date = timezone.now() - timedelta(days=days)
        
        total_dialogs = DialogLog.objects.filter(
            created_at__gte=since_date
        ).count()
        
        successful_dialogs = DialogLog.objects.filter(
            created_at__gte=since_date,
            intent__in=['appointment_confirmed', 'appointment']
        ).count()
        
        return {
            'total_dialogs': total_dialogs,
            'successful_dialogs': successful_dialogs,
            'success_rate': round(
                (successful_dialogs / max(total_dialogs, 1)) * 100, 2
            )
        }
    
    def get_popular_services(self, days=30):
        """Самые популярные услуги"""
        since_date = timezone.now() - timedelta(days=days)
        
        services = Appointment.objects.filter(
            created_at__gte=since_date
        ).values('service__name').annotate(
            count=Count('service')
        ).order_by('-count')
        
        return list(services[:10])
    
    def get_peak_hours(self, days=7):
        """Пиковые часы обращений"""
        since_date = timezone.now() - timedelta(days=days)
        
        from django.db.models import Extract
        
        hours = DialogLog.objects.filter(
            created_at__gte=since_date
        ).extra(
            select={'hour': "strftime('%%H', created_at)"}
        ).values('hour').annotate(
            count=Count('hour')
        ).order_by('-count')
        
        return list(hours[:5])
