"""
Система валидации данных для Smart Secretary
Интеграция с админкой и базой данных
"""

import re
import logging
from typing import Tuple, Optional, Dict, Any
from datetime import datetime, time
from django.core.cache import cache
from django.utils import timezone
from .models import Specialist, Service, Appointment

logger = logging.getLogger(__name__)


class NameValidator:
    """Валидация имен по языкам"""
    
    @staticmethod
    def validate_name(name: str) -> Tuple[bool, str]:
        """
        Валидация имени по языку
        Возвращает: (is_valid, error_message)
        """
        if not name or len(name.strip()) < 2:
            return False, "Имя должно содержать минимум 2 символа"
        
        name_clean = name.strip()
        
        # Проверка на смешанные языки
        has_cyrillic = bool(re.search(r'[а-яё]', name_clean.lower()))
        has_hebrew = bool(re.search(r'[\u0590-\u05FF]', name_clean))
        has_latin = bool(re.search(r'[a-z]', name_clean.lower()))
        
        language_count = sum([has_cyrillic, has_hebrew, has_latin])
        
        if language_count > 1:
            return False, "Имя должно быть на одном языке (русский, иврит или английский)"
        
        # Проверка на служебные слова
        exclude_words = [
            'на', 'к', 'у', 'для', 'запись', 'прием', 'консультация', 
            'массаж', 'диагностика', 'остеопат', 'специалист', 'врач',
            'на массаж', 'на консультацию', 'на диагностику', 'на прием'
        ]
        
        if name_clean.lower() in exclude_words:
            return False, "Это не похоже на имя. Пожалуйста, укажите ваше настоящее имя"
        
        return True, "OK"


class PhoneValidator:
    """Валидация телефонов по коду страны"""
    
    @staticmethod
    def validate_phone(phone: str) -> Tuple[bool, str, str]:
        """
        Валидация телефона с определением страны
        Возвращает: (is_valid, country_code, formatted_phone)
        """
        if not phone:
            return False, "UNKNOWN", "Телефон не может быть пустым"
        
        # Очищаем номер от всех символов кроме цифр и +
        phone_clean = re.sub(r'[^\d+]', '', phone)
        
        # Израильские номера
        if phone_clean.startswith('+972') or phone_clean.startswith('972'):
            if len(phone_clean) in [12, 13]:  # +972501234567 или 972501234567
                formatted = f"+972{phone_clean[-9:]}"  # Нормализуем к +972501234567
                return True, "IL", formatted
            return False, "IL", "Неверный формат израильского номера (+972501234567)"
        
        # Российские номера
        if phone_clean.startswith('+7') or phone_clean.startswith('7'):
            if len(phone_clean) in [11, 12]:  # +79123456789 или 79123456789
                formatted = f"+7{phone_clean[-10:]}"  # Нормализуем к +79123456789
                return True, "RU", formatted
            return False, "RU", "Неверный формат российского номера (+79123456789)"
        
        # Украинские номера
        if phone_clean.startswith('+380') or phone_clean.startswith('380'):
            if len(phone_clean) in [12, 13]:
                formatted = f"+380{phone_clean[-9:]}"
                return True, "UA", formatted
            return False, "UA", "Неверный формат украинского номера (+380501234567)"
        
        # ИСПРАВЛЕНО: Если номер начинается с 0 (локальный израильский формат)
        if phone_clean.startswith('0') and len(phone_clean) in [9, 10]:
            # 0501234567 (10 цифр) или 050123456 (9 цифр - старый формат)
            formatted = f"+972{phone_clean[1:]}"  # Убираем 0, добавляем +972
            return True, "IL", formatted
        
        # ИСПРАВЛЕНО: Если номер из 9 цифр без префикса (израильский без 0)
        if len(phone_clean) == 9 and phone_clean[0] in ['5', '7']:  # Мобильные начинаются с 5 или 7
            formatted = f"+972{phone_clean}"
            return True, "IL", formatted
        
        return False, "UNKNOWN", "Неизвестный формат номера. Поддерживаются: +972501234567, 0501234567, 501234567, +79123456789, +380501234567"


class ServiceValidator:
    """Валидация специалистов и услуг с интеграцией с БД"""
    
    @staticmethod
    def validate_specialist(specialist_name: str) -> Tuple[bool, str, Optional[Specialist]]:
        """
        Проверка существования специалиста в БД
        Возвращает: (is_valid, error_message, specialist_object)
        """
        if not specialist_name:
            return False, "Специалист не указан", None
        
        try:
            # Поиск по точному совпадению (регистронезависимо)
            specialist = Specialist.objects.get(name__iexact=specialist_name.strip())
            logger.info(f"Specialist found: {specialist.name}")
            return True, "OK", specialist
        except Specialist.DoesNotExist:
            # Поиск по частичному совпадению
            specialists = Specialist.objects.filter(name__icontains=specialist_name.strip())
            if specialists.exists():
                specialist = specialists.first()
                logger.info(f"Specialist found by partial match: {specialist.name}")
                return True, f"Найден специалист: {specialist.name}", specialist
            
            # Получаем список доступных специалистов
            available = list(Specialist.objects.values_list('name', flat=True))
            available_str = ", ".join(available)
            
            logger.warning(f"Specialist not found: {specialist_name}")
            return False, f"Специалист '{specialist_name}' не найден. Доступны: {available_str}", None
    
    @staticmethod
    def validate_service(service_name: str) -> Tuple[bool, str, Optional[Service]]:
        """
        Проверка существования услуги в БД
        Возвращает: (is_valid, error_message, service_object)
        """
        if not service_name:
            return False, "Услуга не указана", None
        
        try:
            # Поиск по точному совпадению (регистронезависимо)
            service = Service.objects.get(name__iexact=service_name.strip())
            logger.info(f"Service found: {service.name}")
            return True, "OK", service
        except Service.DoesNotExist:
            # Поиск по частичному совпадению
            services = Service.objects.filter(name__icontains=service_name.strip())
            if services.exists():
                service = services.first()
                logger.info(f"Service found by partial match: {service.name}")
                return True, f"Найдена услуга: {service.name}", service
            
            # Получаем список доступных услуг
            available = list(Service.objects.values_list('name', flat=True))
            available_str = ", ".join(available)
            
            logger.warning(f"Service not found: {service_name}")
            return False, f"Услуга '{service_name}' не найдена. Доступны: {available_str}", None


class AvailabilityValidator:
    """Валидация доступности времени с интеграцией с админкой"""
    
    @staticmethod
    def check_availability(specialist: Specialist, date: datetime.date, 
                          time_obj: datetime.time, duration: int = 60) -> Tuple[bool, str]:
        """
        Проверка доступности времени с учетом админки
        Возвращает: (is_available, error_message)
        """
        try:
            # Проверка рабочих часов (9:00-19:00)
            if not (9 <= time_obj.hour < 19):
                return False, "Центр работает с 9:00 до 19:00"
            
            # Проверка выходных дней
            if date.weekday() in [5, 6]:  # Сб, Вс
                return False, "Центр не работает в субботу и воскресенье"
            
            # Проверка, что дата и время не в прошлом
            now = timezone.now()
            today = now.date()
            
            if date < today:
                return False, "Нельзя записаться на прошедшую дату"
            
            # Если дата сегодня, проверяем время
            if date == today:
                current_time = now.time()
                # Добавляем буфер в 1 час для подготовки
                buffer_time = (now + timezone.timedelta(hours=1)).time()
                if time_obj <= buffer_time:
                    return False, f"Нельзя записаться на время ранее {buffer_time.strftime('%H:%M')} (нужно время для подготовки)"
            
            # Проверка времени окончания процедуры
            end_time = datetime.combine(date, time_obj) + timezone.timedelta(minutes=duration)
            if end_time.time() > time(19, 0):
                return False, f"Процедура не завершится в рабочее время (до 19:00)"
            
            # Проверка существующих записей в БД
            start_datetime = timezone.make_aware(datetime.combine(date, time_obj))
            end_datetime = start_datetime + timezone.timedelta(minutes=duration)
            
            conflicts = Appointment.objects.filter(
                specialist=specialist,
                start_time__date=date,
                status__in=['pending', 'confirmed'],
                start_time__lt=end_datetime,
                end_time__gt=start_datetime
            ).exists()
            
            if conflicts:
                return False, "Это время уже занято. Выберите другое время"
            
            logger.info(f"Time slot available: {specialist.name} on {date} at {time_obj}")
            return True, "OK"
            
        except Exception as e:
            logger.error(f"Error checking availability: {e}")
            return False, f"Ошибка проверки доступности: {str(e)}"
    
    @staticmethod
    def get_available_slots(specialist: Specialist, date: datetime.date, 
                          service_duration: int = 60) -> list:
        """
        Получение доступных слотов времени для специалиста на дату
        Интеграция с админкой для актуальных данных
        """
        try:
            # Кэширование на 5 минут для производительности
            cache_key = f"slots_{specialist.id}_{date}_{service_duration}"
            cached_slots = cache.get(cache_key)
            
            if cached_slots:
                return cached_slots
            
            # Получаем существующие записи из БД
            existing_appointments = Appointment.objects.filter(
                specialist=specialist,
                start_time__date=date,
                status__in=['pending', 'confirmed']
            ).values('start_time', 'end_time')
            
            # Генерируем доступные слоты
            available_slots = []
            start_hour = 9
            end_hour = 19
            
            # Получаем текущее время для фильтрации прошедших слотов
            now = timezone.now()
            today = now.date()
            
            for hour in range(start_hour, end_hour):
                for minute in [0, 30]:  # Слоты каждые 30 минут
                    slot_time = time(hour, minute)
                    slot_datetime = timezone.make_aware(datetime.combine(date, slot_time))
                    
                    # Пропускаем прошедшие слоты для сегодняшней даты
                    if date == today:
                        buffer_time = now + timezone.timedelta(hours=1)
                        if slot_datetime <= buffer_time:
                            continue
                    
                    # Проверяем конфликты с существующими записями
                    slot_end = slot_datetime + timezone.timedelta(minutes=service_duration)
                    
                    has_conflict = False
                    for appointment in existing_appointments:
                        apt_start = appointment['start_time']
                        apt_end = appointment['end_time']
                        
                        if (slot_datetime < apt_end and slot_end > apt_start):
                            has_conflict = True
                            break
                    
                    if not has_conflict:
                        available_slots.append({
                            'time': slot_time.strftime('%H:%M'),
                            'datetime': slot_datetime.isoformat(),
                            'available': True
                        })
            
            # Кэшируем результат
            cache.set(cache_key, available_slots, 300)  # 5 минут
            
            logger.info(f"Generated {len(available_slots)} available slots for {specialist.name} on {date}")
            return available_slots
            
        except Exception as e:
            logger.error(f"Error getting available slots: {e}")
            return []


class ValidationManager:
    """Главный менеджер валидации - интеграция всех компонентов"""
    
    def __init__(self):
        self.name_validator = NameValidator()
        self.phone_validator = PhoneValidator()
        self.service_validator = ServiceValidator()
        self.availability_validator = AvailabilityValidator()
    
    def validate_appointment_data(self, name: str, phone: str, service_name: str, 
                               specialist_name: str, date: str, time_str: str) -> Dict[str, Any]:
        """
        Комплексная валидация всех данных записи
        Возвращает результат валидации с детальной информацией
        """
        result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'data': {},
            'suggestions': []
        }
        
        # 1. Валидация имени
        name_valid, name_error = self.name_validator.validate_name(name)
        if not name_valid:
            result['is_valid'] = False
            result['errors'].append(f"Имя: {name_error}")
        else:
            result['data']['name'] = name.strip()
        
        # 2. Валидация телефона
        phone_valid, country, formatted_phone = self.phone_validator.validate_phone(phone)
        if not phone_valid:
            result['is_valid'] = False
            result['errors'].append(f"Телефон: {formatted_phone}")
        else:
            result['data']['phone'] = formatted_phone
            result['data']['country'] = country
        
        # 3. Валидация услуги
        service_valid, service_error, service_obj = self.service_validator.validate_service(service_name)
        if not service_valid:
            result['is_valid'] = False
            result['errors'].append(f"Услуга: {service_error}")
        else:
            result['data']['service'] = service_obj
            if service_error != "OK":
                result['warnings'].append(f"Услуга: {service_error}")
        
        # 4. Валидация специалиста
        specialist_valid, specialist_error, specialist_obj = self.service_validator.validate_specialist(specialist_name)
        if not specialist_valid:
            result['is_valid'] = False
            result['errors'].append(f"Специалист: {specialist_error}")
        else:
            result['data']['specialist'] = specialist_obj
            if specialist_error != "OK":
                result['warnings'].append(f"Специалист: {specialist_error}")
        
        # 5. Валидация даты и времени (только если все остальное валидно)
        if result['is_valid'] and specialist_obj and date and time_str:
            try:
                # ИСПРАВЛЕНО: Очищаем дату от лишнего текста (например, "(среда)")
                import re
                date_clean = date.strip()
                # Убираем всё что в скобках
                date_clean = re.sub(r'\s*\([^)]*\)', '', date_clean).strip()
                
                # Парсим дату (поддержка разных форматов)
                from .calendar_manager import DateParser
                date_parser = DateParser()
                
                # Пробуем распарсить относительную дату (завтра, среда, и т.д.)
                parsed_datetime = date_parser.extract_datetime(date_clean)
                if parsed_datetime:
                    parsed_date = parsed_datetime.date()
                else:
                    # Пробуем ISO формат
                    parsed_date = datetime.strptime(date_clean, '%Y-%m-%d').date()
                
                # Парсим время
                parsed_time = datetime.strptime(time_str, '%H:%M').time()
                
                # Проверяем доступность
                duration = service_obj.duration if service_obj else 60
                available, availability_error = self.availability_validator.check_availability(
                    specialist_obj, parsed_date, parsed_time, duration
                )
                
                if not available:
                    result['is_valid'] = False
                    result['errors'].append(f"Время: {availability_error}")
                    
                    # Предлагаем альтернативные слоты
                    alternative_slots = self.availability_validator.get_available_slots(
                        specialist_obj, parsed_date, duration
                    )
                    if alternative_slots:
                        result['suggestions'] = [slot['time'] for slot in alternative_slots[:5]]
                else:
                    result['data']['date'] = parsed_date
                    result['data']['time'] = parsed_time
                    
            except ValueError as e:
                result['is_valid'] = False
                result['errors'].append(f"Неверный формат даты/времени: {str(e)}")
        
        # Логирование результата валидации
        if result['is_valid']:
            logger.debug(f"Validation successful for: {name}, {formatted_phone}")
        else:
            # Используем debug вместо warning для уменьшения шума в логах
            logger.debug(f"Validation failed: {result['errors']}")
        
        return result
    
    def get_validation_summary(self, validation_result: Dict[str, Any]) -> str:
        """
        Генерирует понятное сообщение о результатах валидации
        """
        if validation_result['is_valid']:
            message = "✅ Все данные корректны!"
            if validation_result['warnings']:
                message += f"\n⚠️ Предупреждения: {'; '.join(validation_result['warnings'])}"
            return message
        else:
            message = "❌ Обнаружены ошибки:\n"
            for error in validation_result['errors']:
                message += f"• {error}\n"
            
            if validation_result['suggestions']:
                message += f"\n💡 Рекомендуемые времена: {', '.join(validation_result['suggestions'])}"
            
            return message.strip()
