"""
API для валидации в админке в реальном времени
"""

import json
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.views import View
from core.validators import ValidationManager
from core.models import Specialist, Service, Patient, Appointment


@staff_member_required
@csrf_exempt
@require_http_methods(["POST"])
def validate_appointment_data(request):
    """AJAX валидация данных записи"""
    try:
        data = json.loads(request.body)
        
        # Извлекаем данные
        name = data.get('name', '')
        phone = data.get('phone', '')
        service_name = data.get('service', '')
        specialist_name = data.get('specialist', '')
        date = data.get('date', '')
        time = data.get('time', '')
        appointment_id = data.get('appointment_id')  # Для редактирования
        
        # Валидация
        validator = ValidationManager()
        
        if appointment_id:
            # При редактировании исключаем текущую запись
            result = validator.validate_appointment_edit(
                appointment_id, name, phone, service_name, 
                specialist_name, date, time
            )
        else:
            result = validator.validate_appointment_data(
                name, phone, service_name, specialist_name, date, time
            )
        
        return JsonResponse({
            'is_valid': result['is_valid'],
            'errors': result['errors'],
            'warnings': result['warnings'],
            'suggestions': result['suggestions'],
            'alternatives': result['alternatives']
        })
        
    except Exception as e:
        return JsonResponse({
            'is_valid': False,
            'errors': [f'Ошибка валидации: {str(e)}'],
            'warnings': [],
            'suggestions': [],
            'alternatives': []
        }, status=500)


@staff_member_required
@csrf_exempt
@require_http_methods(["POST"])
def get_available_slots(request):
    """Получение доступных слотов времени"""
    try:
        data = json.loads(request.body)
        
        specialist_id = data.get('specialist_id')
        date = data.get('date')
        service_id = data.get('service_id')
        
        if not all([specialist_id, date]):
            return JsonResponse({
                'success': False,
                'error': 'Не указан специалист или дата'
            })
        
        # Получаем объекты
        try:
            specialist = Specialist.objects.get(id=specialist_id)
        except Specialist.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Специалист не найден'
            })
        
        # Определяем длительность процедуры
        duration = 60  # По умолчанию
        if service_id:
            try:
                service = Service.objects.get(id=service_id)
                duration = service.duration
            except Service.DoesNotExist:
                pass
        
        # Парсим дату
        try:
            date_obj = datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({
                'success': False,
                'error': 'Неверный формат даты'
            })
        
        # Получаем доступные слоты
        from core.validators import AvailabilityValidator
        availability_validator = AvailabilityValidator()
        
        slots = availability_validator.get_available_slots(
            specialist, date_obj, duration
        )
        
        return JsonResponse({
            'success': True,
            'slots': slots,
            'date': date,
            'specialist': specialist.name,
            'duration': duration
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Ошибка получения слотов: {str(e)}'
        }, status=500)


@staff_member_required
@csrf_exempt
@require_http_methods(["POST"])
def check_conflicts(request):
    """Проверка конфликтов времени"""
    try:
        data = json.loads(request.body)
        
        specialist_id = data.get('specialist_id')
        start_datetime = data.get('start_datetime')
        end_datetime = data.get('end_datetime')
        appointment_id = data.get('appointment_id')
        
        if not all([specialist_id, start_datetime, end_datetime]):
            return JsonResponse({
                'success': False,
                'error': 'Не указаны обязательные параметры'
            })
        
        # Получаем специалиста
        try:
            specialist = Specialist.objects.get(id=specialist_id)
        except Specialist.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Специалист не найден'
            })
        
        # Парсим даты
        try:
            start_dt = datetime.fromisoformat(start_datetime.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_datetime.replace('Z', '+00:00'))
        except ValueError:
            return JsonResponse({
                'success': False,
                'error': 'Неверный формат даты/времени'
            })
        
        # Проверяем конфликты
        from core.validators import ConflictValidator
        conflict_validator = ConflictValidator()
        
        has_conflicts, conflict_descriptions = conflict_validator.check_appointment_conflicts(
            specialist, start_dt, end_dt, appointment_id
        )
        
        return JsonResponse({
            'success': True,
            'has_conflicts': has_conflicts,
            'conflicts': conflict_descriptions
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Ошибка проверки конфликтов: {str(e)}'
        }, status=500)


@staff_member_required
@csrf_exempt
@require_http_methods(["POST"])
def validate_patient_data(request):
    """Валидация данных пациента"""
    try:
        data = json.loads(request.body)
        
        name = data.get('name', '')
        phone = data.get('phone', '')
        email = data.get('email', '')
        
        from core.validators import NameValidator, PhoneValidator
        
        result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'suggestions': []
        }
        
        # Валидация имени
        if name:
            name_valid, name_error = NameValidator.validate_name(name)
            if not name_valid:
                result['is_valid'] = False
                result['errors'].append(f'Имя: {name_error}')
                result['suggestions'].extend(NameValidator.suggest_corrections(name))
            else:
                normalized_name = NameValidator.normalize_name(name)
                if normalized_name != name.strip():
                    result['warnings'].append(f'Рекомендуется: {normalized_name}')
        
        # Валидация телефона
        if phone:
            phone_valid, country, phone_result = PhoneValidator.validate_phone(phone)
            if not phone_valid:
                result['is_valid'] = False
                result['errors'].append(f'Телефон: {phone_result}')
                result['suggestions'].extend(PhoneValidator.suggest_corrections(phone))
            else:
                if phone_result != phone.strip():
                    result['warnings'].append(f'Рекомендуется: {phone_result}')
        
        # Проверка дубликатов телефона
        if phone and result['is_valid']:
            existing_patients = Patient.objects.filter(phone=phone)
            patient_id = data.get('patient_id')
            if patient_id:
                existing_patients = existing_patients.exclude(id=patient_id)
            
            if existing_patients.exists():
                result['warnings'].append(
                    f'Пациент с таким телефоном уже существует: {existing_patients.first().name}'
                )
        
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({
            'is_valid': False,
            'errors': [f'Ошибка валидации: {str(e)}'],
            'warnings': [],
            'suggestions': []
        }, status=500)


@staff_member_required
@csrf_exempt
@require_http_methods(["GET"])
def get_patient_suggestions(request):
    """Получение предложений пациентов для автокомплита"""
    try:
        query = request.GET.get('q', '').strip()
        
        if len(query) < 2:
            return JsonResponse({'suggestions': []})
        
        # Поиск по имени и телефону
        patients = Patient.objects.filter(
            Q(name__icontains=query) | Q(phone__icontains=query)
        ).order_by('name')[:10]
        
        suggestions = []
        for patient in patients:
            suggestions.append({
                'id': patient.id,
                'name': patient.name,
                'phone': patient.phone,
                'email': patient.email or '',
                'label': f'{patient.name} ({patient.phone})'
            })
        
        return JsonResponse({'suggestions': suggestions})
        
    except Exception as e:
        return JsonResponse({
            'suggestions': [],
            'error': str(e)
        }, status=500)


@method_decorator(staff_member_required, name='dispatch')
class AdminValidationAPI(View):
    """Класс для обработки различных типов валидации в админке"""
    
    def post(self, request, validation_type):
        """Обработка POST запросов валидации"""
        try:
            data = json.loads(request.body)
            
            if validation_type == 'appointment':
                return self.validate_appointment(data)
            elif validation_type == 'patient':
                return self.validate_patient(data)
            elif validation_type == 'conflicts':
                return self.check_conflicts(data)
            elif validation_type == 'slots':
                return self.get_available_slots(data)
            else:
                return JsonResponse({
                    'success': False,
                    'error': f'Неизвестный тип валидации: {validation_type}'
                }, status=400)
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Ошибка обработки запроса: {str(e)}'
            }, status=500)
    
    def validate_appointment(self, data):
        """Валидация записи"""
        validator = ValidationManager()
        
        result = validator.validate_appointment_data(
            data.get('name', ''),
            data.get('phone', ''),
            data.get('service', ''),
            data.get('specialist', ''),
            data.get('date', ''),
            data.get('time', ''),
            data.get('appointment_id')
        )
        
        return JsonResponse({
            'success': True,
            'validation': result
        })
    
    def validate_patient(self, data):
        """Валидация пациента"""
        # Реализация аналогична validate_patient_data
        pass
    
    def check_conflicts(self, data):
        """Проверка конфликтов"""
        # Реализация аналогична check_conflicts
        pass
    
    def get_available_slots(self, data):
        """Получение доступных слотов"""
        # Реализация аналогично get_available_slots
        pass
