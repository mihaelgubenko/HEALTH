"""
Константы и логика для работы с часами работы центра
"""
from datetime import datetime, time
from typing import Tuple, Optional


class WorkHours:
    """Класс для управления часами работы центра"""
    
    # Часы работы по дням недели
    # None - не работаем
    SCHEDULE = {
        0: (10, 19),  # Понедельник: 10:00 - 19:00
        1: (10, 19),  # Вторник: 10:00 - 19:00
        2: (10, 19),  # Среда: 10:00 - 19:00
        3: (10, 19),  # Четверг: 10:00 - 19:00
        4: None,      # Пятница: выходной
        5: None,      # Суббота: Не работаем
        6: (10, 19),  # Воскресенье: 10:00 - 19:00
    }
    
    # Названия дней для сообщений
    DAY_NAMES = {
        0: 'Понедельник',
        1: 'Вторник',
        2: 'Среда',
        3: 'Четверг',
        4: 'Пятница',
        5: 'Суббота',
        6: 'Воскресенье',
    }
    
    @classmethod
    def is_work_day(cls, date: datetime.date) -> bool:
        """
        Проверяет, является ли день рабочим
        
        Args:
            date: Дата для проверки
            
        Returns:
            True если рабочий день, False если выходной
        """
        weekday = date.weekday()
        return cls.SCHEDULE.get(weekday) is not None
    
    @classmethod
    def get_work_hours(cls, date: datetime.date) -> Optional[Tuple[int, int]]:
        """
        Получает часы работы для конкретной даты
        
        Args:
            date: Дата для проверки
            
        Returns:
            Кортеж (час_начала, час_окончания) или None если не рабочий день
        """
        weekday = date.weekday()
        return cls.SCHEDULE.get(weekday)
    
    @classmethod
    def get_work_start_time(cls, date: datetime.date) -> Optional[time]:
        """
        Получает время начала работы для даты
        
        Args:
            date: Дата для проверки
            
        Returns:
            Объект time с временем начала работы или None
        """
        hours = cls.get_work_hours(date)
        if hours:
            return time(hour=hours[0], minute=0)
        return None
    
    @classmethod
    def get_work_end_time(cls, date: datetime.date) -> Optional[time]:
        """
        Получает время окончания работы для даты
        
        Args:
            date: Дата для проверки
            
        Returns:
            Объект time с временем окончания работы или None
        """
        hours = cls.get_work_hours(date)
        if hours:
            return time(hour=hours[1], minute=0)
        return None
    
    @classmethod
    def is_within_work_hours(cls, dt: datetime) -> bool:
        """
        Проверяет, попадает ли время в рабочие часы
        
        Args:
            dt: Дата и время для проверки
            
        Returns:
            True если в рабочее время, False если нет
        """
        if not cls.is_work_day(dt.date()):
            return False
        
        hours = cls.get_work_hours(dt.date())
        if not hours:
            return False
        
        start_hour, end_hour = hours
        current_hour = dt.hour
        
        # Проверяем, что время попадает в рабочие часы
        if current_hour < start_hour or current_hour >= end_hour:
            return False
        
        # Если последний час работы, проверяем минуты
        if current_hour == end_hour - 1 and dt.minute > 30:
            return False
        
        return True
    
    @classmethod
    def get_schedule_text(cls) -> str:
        """
        Получает текстовое описание расписания для отображения пользователю
        
        Returns:
            Строка с расписанием
        """
        return """🕐 Часы работы:
• Вс, Пн, Вт, Ср, Чт: 10:00-19:00
• Пт: Не работаем
• Сб: Не работаем"""
    
    @classmethod
    def get_schedule_html(cls) -> str:
        """
        Получает HTML описание расписания для шаблонов
        
        Returns:
            HTML строка с расписанием
        """
        return """
        <div class="work-hours">
            <p><strong>Воскресенье, Понедельник - Четверг:</strong> 10:00 - 19:00</p>
            <p><strong>Пятница:</strong> Не работаем</p>
            <p><strong>Суббота:</strong> Не работаем</p>
        </div>
        """
    
    @classmethod
    def get_day_info(cls, date: datetime.date) -> str:
        """
        Получает информацию о рабочем дне для сообщений
        
        Args:
            date: Дата для проверки
            
        Returns:
            Строка с информацией о дне
        """
        weekday = date.weekday()
        day_name = cls.DAY_NAMES.get(weekday, 'Неизвестно')
        hours = cls.get_work_hours(date)
        
        if hours is None:
            return f"{day_name}: Не работаем"
        
        start_hour, end_hour = hours
        if weekday == 4:  # Пятница
            return f"{day_name}: {start_hour:02d}:00 - {end_hour:02d}:00 (по договоренности)"
        
        return f"{day_name}: {start_hour:02d}:00 - {end_hour:02d}:00"

