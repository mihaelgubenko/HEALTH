"""
📅 КАЛЕНДАРНЫЙ МЕНЕДЖЕР
Управление внутренним календарем и синхронизацией с сайтом
"""

from datetime import datetime, timedelta, time
from typing import List, Dict, Optional, Tuple
from django.utils import timezone
from django.db.models import Q
from .models import Appointment, Specialist, Service, Patient

class InternalCalendar:
    """Внутренний календарь на основе БД"""
    
    def __init__(self):
        self.timezone = timezone.get_current_timezone()
    
    def get_available_slots(self, specialist: Specialist, date: datetime.date, 
                          service_duration: int = 60) -> List[Dict]:
        """
        Получить доступные слоты для специалиста на дату
        
        Args:
            specialist: Специалист
            date: Дата
            service_duration: Длительность услуги в минутах
            
        Returns:
            List[Dict]: Список доступных слотов
        """
        # Рабочие часы специалиста (10:00 - 19:00)
        work_start = time(10, 0)
        work_end = time(19, 0)
        
        # Получаем занятые слоты
        busy_slots = self._get_busy_slots(specialist, date)
        
        # Генерируем доступные слоты
        available_slots = []
        current_time = datetime.combine(date, work_start)
        end_time = datetime.combine(date, work_end)
        
        while current_time + timedelta(minutes=service_duration) <= end_time:
            slot_end = current_time + timedelta(minutes=service_duration)
            
            # Проверяем, не пересекается ли слот с занятыми
            if not self._is_slot_busy(current_time, slot_end, busy_slots):
                available_slots.append({
                    'start_time': current_time,
                    'end_time': slot_end,
                    'formatted_time': current_time.strftime('%H:%M'),
                    'formatted_date': current_time.strftime('%d.%m.%Y')
                })
            
            # Переходим к следующему слоту (каждые 30 минут)
            current_time += timedelta(minutes=30)
        
        return available_slots
    
    def _get_busy_slots(self, specialist: Specialist, date: datetime.date) -> List[Dict]:
        """Получить занятые слоты специалиста на дату"""
        appointments = Appointment.objects.filter(
            specialist=specialist,
            start_time__date=date,
            status__in=['pending', 'confirmed']
        ).order_by('start_time')
        
        busy_slots = []
        for appointment in appointments:
            busy_slots.append({
                'start_time': appointment.start_time,
                'end_time': appointment.end_time
            })
        
        return busy_slots
    
    def _is_slot_busy(self, slot_start: datetime, slot_end: datetime, 
                     busy_slots: List[Dict]) -> bool:
        """Проверить, занят ли слот"""
        for busy_slot in busy_slots:
            # Проверяем пересечение временных интервалов
            if (slot_start < busy_slot['end_time'] and 
                slot_end > busy_slot['start_time']):
                return True
        return False
    
    def check_conflict(self, specialist: Specialist, start_time: datetime, 
                      end_time: datetime) -> bool:
        """Проверить конфликт времени"""
        conflicts = Appointment.objects.filter(
            specialist=specialist,
            start_time__lt=end_time,
            end_time__gt=start_time,
            status__in=['pending', 'confirmed']
        )
        return conflicts.exists()
    
    def get_appointments_by_date(self, specialist: Specialist, 
                               date: datetime.date) -> List[Appointment]:
        """Получить записи специалиста на дату"""
        return Appointment.objects.filter(
            specialist=specialist,
            start_time__date=date
        ).order_by('start_time')
    
    def get_appointments_by_period(self, specialist: Specialist, 
                                 start_date: datetime.date, 
                                 end_date: datetime.date) -> List[Appointment]:
        """Получить записи специалиста за период"""
        return Appointment.objects.filter(
            specialist=specialist,
            start_time__date__gte=start_date,
            start_time__date__lte=end_date
        ).order_by('start_time')

class CalendarSyncManager:
    """Менеджер календаря (упрощенная версия без внешней синхронизации)"""
    
    def __init__(self):
        self.internal_calendar = InternalCalendar()
    
    # УДАЛЕНО: sync_from_site и sync_to_site (внешняя синхронизация не используется в минимальной конфигурации)
    
    def get_available_slots_with_sync(self, specialist: Specialist, 
                                    date: datetime.date, 
                                    service_duration: int = 60) -> List[Dict]:
        """
        Получить доступные слоты (упрощенная версия без синхронизации)
        
        Args:
            specialist: Специалист
            date: Дата
            service_duration: Длительность услуги
            
        Returns:
            List[Dict]: Доступные слоты
        """
        # Получаем доступные слоты из внутреннего календаря
        return self.internal_calendar.get_available_slots(
            specialist, date, service_duration
        )

class DateParser:
    """Парсер дат и времени для ИИ-секретаря"""
    
    def __init__(self):
        self.relative_dates = {
            'сегодня': 0,
            'завтра': 1,
            'послезавтра': 2,
            'понедельник': self._get_next_weekday(0),
            'вторник': self._get_next_weekday(1),
            'среду': self._get_next_weekday(2),
            'четверг': self._get_next_weekday(3),
            'пятницу': self._get_next_weekday(4),
            'субботу': self._get_next_weekday(5),
            'воскресенье': self._get_next_weekday(6),
        }
    
    def _get_next_weekday(self, weekday: int) -> int:
        """Получить количество дней до следующего дня недели"""
        today = timezone.now().date()
        days_ahead = weekday - today.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        return days_ahead
    
    def extract_datetime(self, text: str) -> Optional[datetime]:
        """
        Извлечь дату и время из текста
        
        Args:
            text: Текст для парсинга
            
        Returns:
            Optional[datetime]: Распознанная дата и время
        """
        text_lower = text.lower().strip()
        
        # Парсим относительные даты
        for date_word, days_offset in self.relative_dates.items():
            if date_word in text_lower:
                target_date = timezone.now().date() + timedelta(days=days_offset)
                
                # Парсим время
                time_match = self._extract_time(text)
                if time_match:
                    hour, minute = time_match
                    return timezone.make_aware(
                        datetime.combine(target_date, time(hour, minute))
                    )
                else:
                    # Если время не указано, возвращаем дату с 10:00
                    return timezone.make_aware(
                        datetime.combine(target_date, time(10, 0))
                    )
        
        return None
    
    def _extract_time(self, text: str) -> Optional[Tuple[int, int]]:
        """Извлечь время из текста"""
        import re
        
        # Паттерны для времени
        time_patterns = [
            r'(\d{1,2}):(\d{2})',  # 9:30, 14:00, 16:00
            r'(\d{1,2})\s*часов?',  # 9 часов, 14 часов, 16 часов
            r'в\s*(\d{1,2})',       # в 9, в 14, в 16
            r'на\s*(\d{1,2})\s*:?\s*(\d{2})?',  # на 16:00, на 16
            r'(\d{1,2})\s*:\s*(\d{2})',  # 16 : 00 (с пробелами)
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, text)
            if match:
                hour = int(match.group(1))
                # Обрабатываем разные случаи групп
                if len(match.groups()) > 1 and match.group(2):
                    minute = int(match.group(2))
                else:
                    minute = 0
                
                # Проверяем корректность времени
                if 0 <= hour <= 23 and 0 <= minute <= 59:
                    return (hour, minute)
        
        return None
    
    def format_available_slots(self, slots: List[Dict]) -> str:
        """
        Форматировать доступные слоты для ИИ-секретаря
        
        Args:
            slots: Список доступных слотов
            
        Returns:
            str: Отформатированная строка
        """
        if not slots:
            return "К сожалению, на эту дату нет свободного времени."
        
        if len(slots) == 1:
            slot = slots[0]
            return f"Доступно время: {slot['formatted_time']} ({slot['formatted_date']})"
        
        # Группируем по датам
        slots_by_date = {}
        for slot in slots:
            date_str = slot['formatted_date']
            if date_str not in slots_by_date:
                slots_by_date[date_str] = []
            slots_by_date[date_str].append(slot['formatted_time'])
        
        result = "Доступное время:\n"
        for date_str, times in slots_by_date.items():
            result += f"• {date_str}: {', '.join(times)}\n"
        
        return result.strip()
