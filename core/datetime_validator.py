"""
Расширенная валидация даты и времени с поддержкой часовых поясов и праздников
"""

import re
from datetime import datetime, date, time, timedelta
from typing import Tuple, List, Dict, Optional, Any
import pytz
from django.utils import timezone
from django.conf import settings


class HolidayManager:
    """Управление праздниками и выходными днями"""
    
    # Фиксированные праздники (месяц, день)
    FIXED_HOLIDAYS = {
        'IL': [
            (1, 1),   # Новый год
            (5, 14),  # День независимости Израиля (приблизительно)
            (9, 30),  # Рош ха-Шана (приблизительно)
            (10, 9),  # Йом Кипур (приблизительно)
        ],
        'RU': [
            (1, 1), (1, 2), (1, 3), (1, 4), (1, 5), (1, 6), (1, 7), (1, 8),  # Новогодние каникулы
            (2, 23),  # День защитника Отечества
            (3, 8),   # Международный женский день
            (5, 1),   # Праздник Весны и Труда
            (5, 9),   # День Победы
            (6, 12),  # День России
            (11, 4),  # День народного единства
        ],
        'UA': [
            (1, 1),   # Новый год
            (1, 7),   # Рождество
            (3, 8),   # Международный женский день
            (5, 1),   # День труда
            (5, 9),   # День победы над нацизмом
            (6, 28),  # День Конституции
            (8, 24),  # День независимости
        ],
        'US': [
            (1, 1),   # New Year's Day
            (7, 4),   # Independence Day
            (12, 25), # Christmas Day
        ]
    }
    
    @staticmethod
    def is_holiday(check_date: date, country: str = 'IL') -> Tuple[bool, str]:
        """
        Проверка, является ли дата праздником
        Возвращает: (is_holiday, holiday_name)
        """
        if country not in HolidayManager.FIXED_HOLIDAYS:
            return False, ""
        
        holidays = HolidayManager.FIXED_HOLIDAYS[country]
        date_tuple = (check_date.month, check_date.day)
        
        if date_tuple in holidays:
            holiday_names = {
                'IL': {
                    (1, 1): "Новый год",
                    (5, 14): "День независимости Израиля",
                    (9, 30): "Рош ха-Шана",
                    (10, 9): "Йом Кипур",
                },
                'RU': {
                    (1, 1): "Новый год", (1, 2): "Новогодние каникулы",
                    (1, 3): "Новогодние каникулы", (1, 4): "Новогодние каникулы",
                    (1, 5): "Новогодние каникулы", (1, 6): "Новогодние каникулы",
                    (1, 7): "Новогодние каникулы", (1, 8): "Новогодние каникулы",
                    (2, 23): "День защитника Отечества",
                    (3, 8): "Международный женский день",
                    (5, 1): "Праздник Весны и Труда",
                    (5, 9): "День Победы",
                    (6, 12): "День России",
                    (11, 4): "День народного единства",
                },
                'UA': {
                    (1, 1): "Новый год",
                    (1, 7): "Рождество",
                    (3, 8): "Международный женский день",
                    (5, 1): "День труда",
                    (5, 9): "День победы над нацизмом",
                    (6, 28): "День Конституции",
                    (8, 24): "День независимости",
                },
                'US': {
                    (1, 1): "New Year's Day",
                    (7, 4): "Independence Day",
                    (12, 25): "Christmas Day",
                }
            }
            
            holiday_name = holiday_names.get(country, {}).get(date_tuple, "Праздник")
            return True, holiday_name
        
        return False, ""
    
    @staticmethod
    def is_weekend(check_date: date, country: str = 'IL') -> bool:
        """Проверка, является ли дата выходным днем"""
        weekday = check_date.weekday()
        
        if country == 'IL':
            # В Израиле выходные: пятница (4) и суббота (5)
            return weekday in [4, 5]
        else:
            # В большинстве стран: суббота (5) и воскресенье (6)
            return weekday in [5, 6]
    
    @staticmethod
    def get_next_working_day(start_date: date, country: str = 'IL') -> date:
        """Получение следующего рабочего дня"""
        current_date = start_date
        max_iterations = 14  # Защита от бесконечного цикла
        
        for _ in range(max_iterations):
            current_date += timedelta(days=1)
            
            if not HolidayManager.is_weekend(current_date, country):
                is_holiday, _ = HolidayManager.is_holiday(current_date, country)
                if not is_holiday:
                    return current_date
        
        # Если не нашли рабочий день за 2 недели, возвращаем дату + 1 день
        return start_date + timedelta(days=1)


class TimezoneManager:
    """Управление часовыми поясами"""
    
    TIMEZONE_MAP = {
        'IL': 'Asia/Jerusalem',
        'RU': 'Europe/Moscow',
        'UA': 'Europe/Kiev',
        'US': 'America/New_York'  # Восточное время по умолчанию
    }
    
    @staticmethod
    def get_timezone(country: str = 'IL') -> pytz.BaseTzInfo:
        """Получение часового пояса для страны"""
        tz_name = TimezoneManager.TIMEZONE_MAP.get(country, 'UTC')
        return pytz.timezone(tz_name)
    
    @staticmethod
    def convert_to_local_time(dt: datetime, country: str = 'IL') -> datetime:
        """Конвертация времени в локальный часовой пояс"""
        if dt.tzinfo is None:
            # Если время без часового пояса, считаем его UTC
            dt = pytz.UTC.localize(dt)
        
        local_tz = TimezoneManager.get_timezone(country)
        return dt.astimezone(local_tz)
    
    @staticmethod
    def get_current_time(country: str = 'IL') -> datetime:
        """Получение текущего времени в указанной стране"""
        local_tz = TimezoneManager.get_timezone(country)
        return datetime.now(local_tz)


class DateTimeValidator:
    """Расширенная валидация даты и времени"""
    
    def __init__(self, country: str = 'IL'):
        self.country = country
        self.timezone = TimezoneManager.get_timezone(country)
        self.holiday_manager = HolidayManager()
        
        # Рабочие часы по странам
        self.working_hours = {
            'IL': {'start': 9, 'end': 19, 'break_start': 13, 'break_end': 14},
            'RU': {'start': 9, 'end': 18, 'break_start': 13, 'break_end': 14},
            'UA': {'start': 9, 'end': 18, 'break_start': 13, 'break_end': 14},
            'US': {'start': 9, 'end': 17, 'break_start': 12, 'break_end': 13}
        }
    
    def parse_date_string(self, date_str: str) -> Tuple[bool, Optional[date], str]:
        """
        Парсинг строки даты в различных форматах
        Возвращает: (success, parsed_date, error_message)
        """
        if not date_str or not date_str.strip():
            return False, None, "Дата не может быть пустой"
        
        date_clean = date_str.strip().lower()
        
        # Убираем лишний текст в скобках
        date_clean = re.sub(r'\s*\([^)]*\)', '', date_clean).strip()
        
        current_date = TimezoneManager.get_current_time(self.country).date()
        
        # Относительные даты
        relative_dates = {
            'сегодня': current_date,
            'завтра': current_date + timedelta(days=1),
            'послезавтра': current_date + timedelta(days=2),
            'today': current_date,
            'tomorrow': current_date + timedelta(days=1),
        }
        
        if date_clean in relative_dates:
            return True, relative_dates[date_clean], ""
        
        # Дни недели
        weekdays = {
            'понедельник': 0, 'вторник': 1, 'среду': 2, 'четверг': 3,
            'пятницу': 4, 'субботу': 5, 'воскресенье': 6,
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6
        }
        
        for day_name, weekday in weekdays.items():
            if day_name in date_clean:
                days_ahead = weekday - current_date.weekday()
                if days_ahead <= 0:  # Если день уже прошел на этой неделе
                    days_ahead += 7
                target_date = current_date + timedelta(days=days_ahead)
                return True, target_date, ""
        
        # Форматы дат
        date_formats = [
            '%Y-%m-%d',      # 2025-10-22
            '%d.%m.%Y',      # 22.10.2025
            '%d/%m/%Y',      # 22/10/2025
            '%d-%m-%Y',      # 22-10-2025
            '%d.%m',         # 22.10 (текущий год)
            '%d/%m',         # 22/10 (текущий год)
        ]
        
        for fmt in date_formats:
            try:
                if '%Y' not in fmt:
                    # Добавляем текущий год
                    parsed_date = datetime.strptime(date_clean, fmt).date()
                    parsed_date = parsed_date.replace(year=current_date.year)
                else:
                    parsed_date = datetime.strptime(date_clean, fmt).date()
                
                return True, parsed_date, ""
            except ValueError:
                continue
        
        return False, None, f"Неверный формат даты: {date_str}. Используйте: ГГГГ-ММ-ДД, ДД.ММ.ГГГГ, 'сегодня', 'завтра' или день недели"
    
    def parse_time_string(self, time_str: str) -> Tuple[bool, Optional[time], str]:
        """
        Парсинг строки времени
        Возвращает: (success, parsed_time, error_message)
        """
        if not time_str or not time_str.strip():
            return False, None, "Время не может быть пустым"
        
        time_clean = time_str.strip()
        
        # Форматы времени
        time_formats = [
            '%H:%M',         # 15:30
            '%H.%M',         # 15.30
            '%H-%M',         # 15-30
            '%H %M',         # 15 30
            '%H',            # 15 (добавляем :00)
        ]
        
        for fmt in time_formats:
            try:
                if fmt == '%H':
                    # Для формата только часов добавляем минуты
                    hour = int(time_clean)
                    if 0 <= hour <= 23:
                        return True, time(hour, 0), ""
                else:
                    parsed_time = datetime.strptime(time_clean, fmt).time()
                    return True, parsed_time, ""
            except ValueError:
                continue
        
        return False, None, f"Неверный формат времени: {time_str}. Используйте: ЧЧ:ММ (например, 15:30)"
    
    def validate_date(self, check_date: date) -> Tuple[bool, str]:
        """Валидация даты"""
        current_date = TimezoneManager.get_current_time(self.country).date()
        
        # Проверка, что дата не в прошлом
        if check_date < current_date:
            return False, "Нельзя записаться на прошедшую дату"
        
        # Проверка на слишком далекое будущее (больше года)
        max_date = current_date + timedelta(days=365)
        if check_date > max_date:
            return False, "Нельзя записаться более чем на год вперед"
        
        # Проверка на выходные дни
        if self.holiday_manager.is_weekend(check_date, self.country):
            next_working = self.holiday_manager.get_next_working_day(check_date, self.country)
            return False, f"Центр не работает в выходные дни. Ближайший рабочий день: {next_working.strftime('%d.%m.%Y')}"
        
        # Проверка на праздники
        is_holiday, holiday_name = self.holiday_manager.is_holiday(check_date, self.country)
        if is_holiday:
            next_working = self.holiday_manager.get_next_working_day(check_date, self.country)
            return False, f"Центр не работает в праздничные дни ({holiday_name}). Ближайший рабочий день: {next_working.strftime('%d.%m.%Y')}"
        
        return True, "OK"
    
    def validate_time(self, check_time: time, check_date: date) -> Tuple[bool, str]:
        """Валидация времени"""
        working_hours = self.working_hours.get(self.country, self.working_hours['IL'])
        
        # Проверка рабочих часов
        if check_time.hour < working_hours['start'] or check_time.hour >= working_hours['end']:
            return False, f"Центр работает с {working_hours['start']:02d}:00 до {working_hours['end']:02d}:00"
        
        # Проверка обеденного перерыва
        if (working_hours['break_start'] <= check_time.hour < working_hours['break_end']):
            return False, f"Обеденный перерыв с {working_hours['break_start']:02d}:00 до {working_hours['break_end']:02d}:00"
        
        # Проверка, что время не в прошлом (если дата сегодня)
        current_datetime = TimezoneManager.get_current_time(self.country)
        current_date = current_datetime.date()
        current_time = current_datetime.time()
        
        if check_date == current_date:
            # Добавляем буфер времени для подготовки
            buffer_minutes = 60  # 1 час
            buffer_time = (current_datetime + timedelta(minutes=buffer_minutes)).time()
            
            if check_time <= buffer_time:
                return False, f"Нельзя записаться на время ранее {buffer_time.strftime('%H:%M')} (нужно время для подготовки)"
        
        return True, "OK"
    
    def validate_datetime(self, date_str: str, time_str: str) -> Dict[str, Any]:
        """
        Комплексная валидация даты и времени
        Возвращает детальную информацию о валидации
        """
        result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'parsed_date': None,
            'parsed_time': None,
            'parsed_datetime': None,
            'suggestions': []
        }
        
        # Парсинг даты
        date_success, parsed_date, date_error = self.parse_date_string(date_str)
        if not date_success:
            result['is_valid'] = False
            result['errors'].append(f"Дата: {date_error}")
        else:
            result['parsed_date'] = parsed_date
            
            # Валидация даты
            date_valid, date_validation_error = self.validate_date(parsed_date)
            if not date_valid:
                result['is_valid'] = False
                result['errors'].append(f"Дата: {date_validation_error}")
        
        # Парсинг времени
        time_success, parsed_time, time_error = self.parse_time_string(time_str)
        if not time_success:
            result['is_valid'] = False
            result['errors'].append(f"Время: {time_error}")
        else:
            result['parsed_time'] = parsed_time
            
            # Валидация времени (только если дата тоже валидна)
            if parsed_date:
                time_valid, time_validation_error = self.validate_time(parsed_time, parsed_date)
                if not time_valid:
                    result['is_valid'] = False
                    result['errors'].append(f"Время: {time_validation_error}")
        
        # Создание объединенного datetime
        if parsed_date and parsed_time:
            try:
                # Создаем datetime в локальном часовом поясе
                naive_datetime = datetime.combine(parsed_date, parsed_time)
                result['parsed_datetime'] = self.timezone.localize(naive_datetime)
            except Exception as e:
                result['is_valid'] = False
                result['errors'].append(f"Ошибка создания datetime: {str(e)}")
        
        return result
    
    def get_available_time_slots(self, check_date: date, duration_minutes: int = 60) -> List[Dict[str, Any]]:
        """Получение доступных временных слотов на дату"""
        slots = []
        
        # Проверяем, что дата валидна
        date_valid, date_error = self.validate_date(check_date)
        if not date_valid:
            return slots
        
        working_hours = self.working_hours.get(self.country, self.working_hours['IL'])
        current_datetime = TimezoneManager.get_current_time(self.country)
        
        # Генерируем слоты каждые 30 минут
        slot_duration = 30  # минут между слотами
        
        start_hour = working_hours['start']
        end_hour = working_hours['end']
        break_start = working_hours['break_start']
        break_end = working_hours['break_end']
        
        current_time = datetime.combine(check_date, time(start_hour, 0))
        end_time = datetime.combine(check_date, time(end_hour, 0))
        
        while current_time < end_time:
            slot_time = current_time.time()
            
            # Пропускаем обеденный перерыв
            if break_start <= slot_time.hour < break_end:
                current_time += timedelta(minutes=slot_duration)
                continue
            
            # Проверяем, что процедура поместится до конца рабочего дня
            procedure_end = current_time + timedelta(minutes=duration_minutes)
            if procedure_end.time() > time(end_hour, 0):
                break
            
            # Проверяем, что время не в прошлом (для сегодняшней даты)
            if check_date == current_datetime.date():
                buffer_time = current_datetime + timedelta(hours=1)
                slot_datetime = self.timezone.localize(current_time)
                
                if slot_datetime <= buffer_time:
                    current_time += timedelta(minutes=slot_duration)
                    continue
            
            # Добавляем слот
            slots.append({
                'time': slot_time.strftime('%H:%M'),
                'datetime': self.timezone.localize(current_time),
                'available': True,  # Здесь можно добавить проверку занятости
                'duration': duration_minutes
            })
            
            current_time += timedelta(minutes=slot_duration)
        
        return slots
    
    def suggest_alternative_dates(self, original_date: date, days_ahead: int = 7) -> List[Dict[str, Any]]:
        """Предложение альтернативных дат"""
        suggestions = []
        current_date = TimezoneManager.get_current_time(self.country).date()
        
        # Начинаем с завтрашнего дня или с исходной даты (если она в будущем)
        start_date = max(current_date + timedelta(days=1), original_date)
        
        for i in range(days_ahead):
            check_date = start_date + timedelta(days=i)
            
            # Проверяем валидность даты
            date_valid, date_error = self.validate_date(check_date)
            if date_valid:
                # Получаем доступные слоты
                available_slots = self.get_available_time_slots(check_date)
                
                if available_slots:
                    suggestions.append({
                        'date': check_date,
                        'date_str': check_date.strftime('%d.%m.%Y'),
                        'weekday': check_date.strftime('%A'),
                        'available_slots': len(available_slots),
                        'first_slot': available_slots[0]['time'] if available_slots else None,
                        'last_slot': available_slots[-1]['time'] if available_slots else None
                    })
        
        return suggestions
