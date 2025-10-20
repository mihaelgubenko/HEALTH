from django.contrib import admin
from django.shortcuts import render
from django.urls import path
from django.db.models import Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Appointment, Service, Patient, DialogLog, ContactMessage


class AdminDashboard:
    """Кастомный дашборд для админки"""
    
    def get_dashboard_data(self):
        """Получение данных для дашборда"""
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        
        # Статистика записей
        appointments_today = Appointment.objects.filter(
            start_time__date=today
        ).count()
        
        appointments_week = Appointment.objects.filter(
            start_time__date__gte=week_ago
        ).count()
        
        appointments_month = Appointment.objects.filter(
            start_time__date__gte=month_ago
        ).count()
        
        # Статистика по статусам
        appointments_by_status = Appointment.objects.values('status').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Популярные услуги
        popular_services = Service.objects.annotate(
            appointment_count=Count('appointment')
        ).filter(appointment_count__gt=0).order_by('-appointment_count')[:5]
        
        # Статистика по специалистам
        specialists_stats = Appointment.objects.values(
            'specialist__id', 'specialist__name', 'specialist__specialty'
        ).annotate(
            appointment_count=Count('id')
        ).order_by('-appointment_count')[:5]
        
        # Последние сообщения
        recent_messages = ContactMessage.objects.filter(
            is_read=False
        ).order_by('-created_at')[:5]
        
        # Статистика пациентов
        total_patients = Patient.objects.count()
        new_patients_month = Patient.objects.filter(
            created_at__date__gte=month_ago
        ).count()
        
        # Статистика по каналам
        channels_stats = Appointment.objects.values('channel').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Данные для графиков (последние 7 дней)
        daily_appointments = []
        for i in range(7):
            date = today - timedelta(days=i)
            count = Appointment.objects.filter(start_time__date=date).count()
            daily_appointments.append({
                'date': date.strftime('%d.%m'),
                'count': count
            })
        daily_appointments.reverse()
        
        return {
            'appointments_today': appointments_today,
            'appointments_week': appointments_week,
            'appointments_month': appointments_month,
            'appointments_by_status': appointments_by_status,
            'popular_services': popular_services,
            'specialists_stats': specialists_stats,
            'recent_messages': recent_messages,
            'total_patients': total_patients,
            'new_patients_month': new_patients_month,
            'channels_stats': channels_stats,
            'daily_appointments': daily_appointments,
        }
    
    def dashboard_view(self, request):
        """Представление дашборда"""
        context = {
            'title': 'Дашборд',
            'dashboard_data': self.get_dashboard_data(),
            'today': timezone.now().date(),
        }
        return render(request, 'admin/dashboard.html', context)


# Создаем экземпляр дашборда
dashboard = AdminDashboard()


def get_admin_urls():
    """Получение URL для админки"""
    return [
        path('dashboard/', dashboard.dashboard_view, name='admin_dashboard'),
    ]
