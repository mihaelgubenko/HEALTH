"""
API views для ИИ-секретаря
"""
import json
import uuid
from datetime import datetime  # ИСПРАВЛЕНО: Добавлен импорт datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from .lite_secretary import LiteSmartSecretary
from .models import Service, Specialist
from .validators import ValidationManager  # ИСПРАВЛЕНО: Добавлена валидация


@method_decorator(csrf_exempt, name='dispatch')
class ChatAPIView(View):
    """API для чата с ИИ-секретарем"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # ТОЛЬКО LiteSecretary - максимальная стабильность (показал 90% в тестах)
        self.secretary_service = LiteSmartSecretary()
    
    def post(self, request):
        """Обрабатывает сообщение пользователя"""
        try:
            data = json.loads(request.body)
            message = data.get('message', '')
            session_id = data.get('session_id', str(uuid.uuid4()))
            
            if not message:
                return JsonResponse({
                    'error': 'Сообщение не может быть пустым'
                }, status=400)
            
            # ИСПРАВЛЕНО: Проверка максимальной длины сообщения
            if len(message) > 500:
                return JsonResponse({
                    'error': 'Сообщение слишком длинное (максимум 500 символов)'
                }, status=400)
            
            # Обрабатываем сообщение через стабильный LiteSecretary
            response = self.secretary_service.process_message(message, session_id)
            
            # ИСПРАВЛЕНО: Возвращаем правильную структуру ответа
            return JsonResponse({
                'reply': response.get('reply', ''),
                'intent': response.get('intent', ''),
                'entities': response.get('entities', {}),
                'session_id': response.get('session_id', session_id),
                'offer_slots': response.get('offer_slots', []),
                'error': response.get('error', None)
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'reply': 'Извините, произошла ошибка при обработке запроса.',
                'intent': 'error',
                'error': 'Неверный JSON',
                'entities': {},
                'session_id': session_id if 'session_id' in locals() else str(uuid.uuid4())
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'reply': f'Извините, произошла ошибка: {str(e)}',
                'intent': 'error',
                'error': str(e),
                'entities': {},
                'session_id': session_id if 'session_id' in locals() else str(uuid.uuid4())
            }, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class AppointmentAPIView(View):
    """API для создания записи на прием"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Используем только LiteSecretary для записей (стабильность приоритет)
        self.secretary_service = LiteSmartSecretary()
    
    def post(self, request):
        """Создает запись на прием"""
        try:
            data = json.loads(request.body)
            
            # Извлекаем данные
            session_id = data.get('session_id')
            name = data.get('name')
            phone = data.get('phone')
            service_name = data.get('service')
            specialist_name = data.get('specialist')
            day = data.get('day')
            time = data.get('time')
            
            # Валидация
            if not all([name, phone, service_name, specialist_name, day, time]):
                return JsonResponse({
                    'error': 'Не все обязательные поля заполнены'
                }, status=400)
            
            # Создаем запись
            success, result = self.secretary_service.create_appointment(
                session_id, name, phone, service_name, specialist_name, day, time
            )
            
            if success:
                return JsonResponse({
                    'success': True,
                    'appointment_id': result.id,
                    'message': 'Запись успешно создана'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': result
                }, status=400)
                
        except json.JSONDecodeError:
            return JsonResponse({
                'error': 'Неверный JSON'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'error': f'Ошибка сервера: {str(e)}'
            }, status=500)


@require_http_methods(["GET"])
def get_services_api(request):
    """API для получения списка услуг"""
    try:
        services = Service.objects.all()
        services_data = []
        
        for service in services:
            services_data.append({
                'id': service.id,
                'name': service.name,
                'description': service.description,
                'price': str(service.price),
                'duration': service.duration
            })
        
        return JsonResponse({
            'services': services_data
        })
        
    except Exception as e:
        return JsonResponse({
            'error': f'Ошибка получения услуг: {str(e)}'
        }, status=500)


@require_http_methods(["GET"])
def get_specialists_api(request):
    """API для получения списка специалистов"""
    try:
        specialists = Specialist.objects.all()
        specialists_data = []
        
        for specialist in specialists:
            specialists_data.append({
                'id': specialist.id,
                'name': specialist.name,
                'specialty': specialist.specialty,
                'description': specialist.description
            })
        
        return JsonResponse({
            'specialists': specialists_data
        })
        
    except Exception as e:
        return JsonResponse({
            'error': f'Ошибка получения специалистов: {str(e)}'
        }, status=500)


@require_http_methods(["GET"])
def get_available_slots_api(request):
    """API для получения доступных слотов времени"""
    try:
        specialist_id = request.GET.get('specialist_id')
        date = request.GET.get('date')
        
        if not specialist_id or not date:
            return JsonResponse({
                'error': 'Необходимы параметры specialist_id и date'
            }, status=400)
        
        # Базовые слоты времени (в реальности нужно проверять занятость)
        slots = [
            "09:00", "10:00", "11:00", "12:00",
            "15:00", "16:00", "17:00", "18:00", "19:00"
        ]
        
        return JsonResponse({
            'slots': slots
        })
        
    except Exception as e:
        return JsonResponse({
            'error': f'Ошибка получения слотов: {str(e)}'
        }, status=500)


# УДАЛЕНО: LearningAPIView (самообучение не используется в минимальной конфигурации)


@method_decorator(csrf_exempt, name='dispatch')
class AppointmentManagementAPIView(View):
    """API для управления записями (проверка, отмена)"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.secretary_service = LiteSmartSecretary()
    
    def get(self, request):
        """Проверяет записи пациента по телефону"""
        try:
            phone = request.GET.get('phone')
            if not phone:
                return JsonResponse({
                    'error': 'Не указан номер телефона'
                }, status=400)
            
            appointments = self.secretary_service.check_appointments(phone)
            
            return JsonResponse({
                'success': True,
                'appointments': appointments,
                'count': len(appointments)
            })
            
        except Exception as e:
            return JsonResponse({
                'error': f'Ошибка проверки записей: {str(e)}'
            }, status=500)
    
    def post(self, request):
        """Отменяет запись"""
        try:
            data = json.loads(request.body)
            appointment_id = data.get('appointment_id')
            
            if not appointment_id:
                return JsonResponse({
                    'error': 'Не указан ID записи'
                }, status=400)
            
            success, message = self.secretary_service.cancel_appointment(appointment_id)
            
            if success:
                return JsonResponse({
                    'success': True,
                    'message': message
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': message
                }, status=400)
                
        except Exception as e:
            return JsonResponse({
                'error': f'Ошибка отмены записи: {str(e)}'
            }, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class ValidationAPIView(View):
    """API для валидации данных записи"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.validator = ValidationManager()
    
    def post(self, request):
        """Валидация данных записи"""
        try:
            data = json.loads(request.body)
            
            # Получаем данные для валидации
            name = data.get('name', '')
            phone = data.get('phone', '')
            service_name = data.get('service', '')
            specialist_name = data.get('specialist', '')
            date = data.get('date', '')
            time_str = data.get('time', '')
            
            # Выполняем валидацию
            validation_result = self.validator.validate_appointment_data(
                name, phone, service_name, specialist_name, date, time_str
            )
            
            # Формируем ответ
            response_data = {
                'is_valid': validation_result['is_valid'],
                'errors': validation_result['errors'],
                'warnings': validation_result['warnings'],
                'suggestions': validation_result['suggestions'],
                'summary': self.validator.get_validation_summary(validation_result)
            }
            
            # Добавляем валидированные данные если все ОК
            if validation_result['is_valid']:
                response_data['validated_data'] = {
                    'name': validation_result['data']['name'],
                    'phone': validation_result['data']['phone'],
                    'country': validation_result['data'].get('country'),
                    'service_id': validation_result['data']['service'].id,
                    'specialist_id': validation_result['data']['specialist'].id,
                    'date': validation_result['data']['date'].isoformat(),
                    'time': validation_result['data']['time'].strftime('%H:%M')
                }
            
            return JsonResponse(response_data)
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Неверный формат JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    def get(self, request):
        """Получение доступных слотов времени"""
        try:
            specialist_id = request.GET.get('specialist_id')
            date = request.GET.get('date')
            
            if not specialist_id or not date:
                return JsonResponse({'error': 'Требуются specialist_id и date'}, status=400)
            
            # Получаем специалиста
            try:
                specialist = Specialist.objects.get(id=specialist_id)
            except Specialist.DoesNotExist:
                return JsonResponse({'error': 'Специалист не найден'}, status=404)
            
            # Парсим дату
            try:
                parsed_date = datetime.strptime(date, '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({'error': 'Неверный формат даты'}, status=400)
            
            # Получаем доступные слоты
            available_slots = self.validator.availability_validator.get_available_slots(
                specialist, parsed_date
            )
            
            return JsonResponse({
                'specialist': specialist.name,
                'date': date,
                'available_slots': available_slots
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
