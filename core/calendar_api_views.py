"""
📅 API ДЛЯ КАЛЕНДАРНОЙ СИСТЕМЫ
API endpoints для работы с календарем и синхронизацией
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from django.utils import timezone
from datetime import datetime, date, timedelta
import json

from .calendar_manager import CalendarSyncManager, DateParser
from .models import Specialist, Service, Appointment

@method_decorator(csrf_exempt, name='dispatch')
class CalendarAPIView(View):
    """API для работы с календарем"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.calendar_manager = CalendarSyncManager()
        self.date_parser = DateParser()
    
    def get(self, request):
        """Получить доступные слоты"""
        try:
            specialist_id = request.GET.get('specialist_id')
            date_str = request.GET.get('date')
            service_id = request.GET.get('service_id')
            
            if not specialist_id or not date_str:
                return JsonResponse({
                    'error': 'Не указаны specialist_id и date'
                }, status=400)
            
            # Парсим дату
            try:
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({
                    'error': 'Неверный формат даты. Используйте YYYY-MM-DD'
                }, status=400)
            
            # Получаем специалиста
            try:
                specialist = Specialist.objects.get(id=specialist_id)
            except Specialist.DoesNotExist:
                return JsonResponse({
                    'error': 'Специалист не найден'
                }, status=404)
            
            # Получаем длительность услуги
            service_duration = 60  # По умолчанию
            if service_id:
                try:
                    service = Service.objects.get(id=service_id)
                    service_duration = service.duration
                except Service.DoesNotExist:
                    pass
            
            # Получаем доступные слоты
            available_slots = self.calendar_manager.get_available_slots_with_sync(
                specialist, target_date, service_duration
            )
            
            # Форматируем результат
            slots = []
            for slot in available_slots:
                slots.append({
                    'start_time': slot['start_time'].strftime('%H:%M'),
                    'end_time': slot['end_time'].strftime('%H:%M'),
                    'datetime': slot['start_time'].isoformat(),
                    'formatted': f"{slot['formatted_time']} ({slot['formatted_date']})"
                })
            
            return JsonResponse({
                'success': True,
                'specialist': specialist.name,
                'date': target_date.strftime('%Y-%m-%d'),
                'available_slots': slots,
                'total_slots': len(slots)
            })
            
        except Exception as e:
            return JsonResponse({
                'error': f'Ошибка сервера: {str(e)}'
            }, status=500)
    
    def post(self, request):
        """Проверить доступность конкретного времени"""
        try:
            data = json.loads(request.body)
            specialist_id = data.get('specialist_id')
            datetime_str = data.get('datetime')
            service_id = data.get('service_id')
            
            if not specialist_id or not datetime_str:
                return JsonResponse({
                    'error': 'Не указаны specialist_id и datetime'
                }, status=400)
            
            # Парсим дату и время
            try:
                target_datetime = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
            except ValueError:
                return JsonResponse({
                    'error': 'Неверный формат datetime'
                }, status=400)
            
            # Получаем специалиста
            try:
                specialist = Specialist.objects.get(id=specialist_id)
            except Specialist.DoesNotExist:
                return JsonResponse({
                    'error': 'Специалист не найден'
                }, status=404)
            
            # Получаем длительность услуги
            service_duration = 60  # По умолчанию
            if service_id:
                try:
                    service = Service.objects.get(id=service_id)
                    service_duration = service.duration
                except Service.DoesNotExist:
                    pass
            
            # Проверяем конфликт
            end_datetime = target_datetime + timedelta(minutes=service_duration)
            has_conflict = self.calendar_manager.internal_calendar.check_conflict(
                specialist, target_datetime, end_datetime
            )
            
            return JsonResponse({
                'success': True,
                'available': not has_conflict,
                'datetime': target_datetime.isoformat(),
                'specialist': specialist.name
            })
            
        except Exception as e:
            return JsonResponse({
                'error': f'Ошибка сервера: {str(e)}'
            }, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class SyncAPIView(View):
    """API для синхронизации с внешним сайтом"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.calendar_manager = CalendarSyncManager()
    
    def post(self, request):
        """Синхронизировать с внешним сайтом"""
        try:
            data = json.loads(request.body)
            action = data.get('action')  # 'sync_from_site' или 'sync_to_site'
            specialist_id = data.get('specialist_id')
            date_str = data.get('date')
            
            if not action or not specialist_id or not date_str:
                return JsonResponse({
                    'error': 'Не указаны action, specialist_id и date'
                }, status=400)
            
            # Получаем специалиста
            try:
                specialist = Specialist.objects.get(id=specialist_id)
            except Specialist.DoesNotExist:
                return JsonResponse({
                    'error': 'Специалист не найден'
                }, status=404)
            
            # Парсим дату
            try:
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({
                    'error': 'Неверный формат даты'
                }, status=400)
            
            # Выполняем синхронизацию
            if action == 'sync_from_site':
                success = self.calendar_manager.sync_from_site(specialist, target_date)
            elif action == 'sync_to_site':
                # Получаем записи для синхронизации
                appointments = Appointment.objects.filter(
                    specialist=specialist,
                    start_time__date=target_date,
                    is_synced=False
                )
                success = True
                for appointment in appointments:
                    if not self.calendar_manager.sync_to_site(appointment):
                        success = False
            else:
                return JsonResponse({
                    'error': 'Неверное действие. Используйте sync_from_site или sync_to_site'
                }, status=400)
            
            return JsonResponse({
                'success': success,
                'action': action,
                'specialist': specialist.name,
                'date': target_date.strftime('%Y-%m-%d')
            })
            
        except Exception as e:
            return JsonResponse({
                'error': f'Ошибка сервера: {str(e)}'
            }, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class DateParserAPIView(View):
    """API для парсинга дат"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.date_parser = DateParser()
    
    def post(self, request):
        """Распарсить дату и время из текста"""
        try:
            data = json.loads(request.body)
            text = data.get('text')
            
            if not text:
                return JsonResponse({
                    'error': 'Не указан текст для парсинга'
                }, status=400)
            
            # Парсим дату и время
            parsed_datetime = self.date_parser.extract_datetime(text)
            
            if parsed_datetime:
                return JsonResponse({
                    'success': True,
                    'parsed_datetime': parsed_datetime.isoformat(),
                    'date': parsed_datetime.date().strftime('%Y-%m-%d'),
                    'time': parsed_datetime.time().strftime('%H:%M'),
                    'formatted': parsed_datetime.strftime('%d.%m.%Y %H:%M')
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Не удалось распознать дату и время в тексте'
                })
            
        except Exception as e:
            return JsonResponse({
                'error': f'Ошибка сервера: {str(e)}'
            }, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class CalendarStatsAPIView(View):
    """API для статистики календаря"""
    
    def get(self, request):
        """Получить статистику календаря"""
        try:
            specialist_id = request.GET.get('specialist_id')
            start_date = request.GET.get('start_date')
            end_date = request.GET.get('end_date')
            
            # Парсим даты
            if start_date:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            else:
                start_date = timezone.now().date() - timedelta(days=30)
            
            if end_date:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            else:
                end_date = timezone.now().date() + timedelta(days=30)
            
            # Фильтр по специалисту
            appointments_filter = Appointment.objects.filter(
                start_time__date__gte=start_date,
                start_time__date__lte=end_date
            )
            
            if specialist_id:
                appointments_filter = appointments_filter.filter(specialist_id=specialist_id)
            
            # Статистика
            total_appointments = appointments_filter.count()
            confirmed_appointments = appointments_filter.filter(status='confirmed').count()
            pending_appointments = appointments_filter.filter(status='pending').count()
            cancelled_appointments = appointments_filter.filter(status='cancelled').count()
            
            # Статистика по дням недели
            weekday_stats = {}
            for appointment in appointments_filter:
                weekday = appointment.start_time.strftime('%A')
                weekday_stats[weekday] = weekday_stats.get(weekday, 0) + 1
            
            return JsonResponse({
                'success': True,
                'period': {
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'end_date': end_date.strftime('%Y-%m-%d')
                },
                'statistics': {
                    'total_appointments': total_appointments,
                    'confirmed': confirmed_appointments,
                    'pending': pending_appointments,
                    'cancelled': cancelled_appointments,
                    'confirmation_rate': (confirmed_appointments / total_appointments * 100) if total_appointments > 0 else 0
                },
                'weekday_distribution': weekday_stats
            })
            
        except Exception as e:
            return JsonResponse({
                'error': f'Ошибка сервера: {str(e)}'
            }, status=500)
