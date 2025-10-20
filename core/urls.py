from django.urls import path
from . import views
from .api_views import ChatAPIView, AppointmentAPIView, AppointmentManagementAPIView, ValidationAPIView, get_services_api, get_specialists_api, get_available_slots_api
from .calendar_api_views import CalendarAPIView, SyncAPIView, DateParserAPIView, CalendarStatsAPIView

app_name = 'core'

urlpatterns = [
    # Главная страница
    path('', views.home, name='home'),
    
    # Страницы услуг
    path('services/', views.services, name='services'),
    path('services/<int:service_id>/', views.service_detail, name='service_detail'),
    
    # Форма записи
    path('appointment/', views.appointment_form, name='appointment_form'),
    path('appointment/success/', views.appointment_success, name='appointment_success'),
    
    # Контакты
    path('contacts/', views.contacts, name='contacts'),
    
    # Чат с ИИ-секретарем
    path('chat/', views.chat, name='chat'),
    
    # API для AJAX
    path('api/specialists/', views.get_specialists, name='get_specialists'),
    path('api/available-slots/', views.get_available_slots, name='get_available_slots'),
    
    # API для ИИ-секретаря
    path('api/chat/', ChatAPIView.as_view(), name='chat_api'),
    path('api/appointment/', AppointmentAPIView.as_view(), name='appointment_api'),
    path('api/appointments/', AppointmentManagementAPIView.as_view(), name='appointments_api'),
    path('api/validation/', ValidationAPIView.as_view(), name='validation_api'),  # ИСПРАВЛЕНО: Добавлена валидация
    path('api/services/', get_services_api, name='services_api'),
    path('api/specialists/', get_specialists_api, name='specialists_api'),
    path('api/slots/', get_available_slots_api, name='slots_api'),
    
    # Календарная система
    path('api/calendar/', CalendarAPIView.as_view(), name='calendar_api'),
    path('api/sync/', SyncAPIView.as_view(), name='sync_api'),
    path('api/date-parser/', DateParserAPIView.as_view(), name='date_parser_api'),
    path('api/calendar-stats/', CalendarStatsAPIView.as_view(), name='calendar_stats_api'),
    
    # Аналитика и мониторинг
    path('analytics/', views.analytics_dashboard, name='analytics'),
]
