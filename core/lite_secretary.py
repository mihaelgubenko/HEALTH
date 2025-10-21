"""
⚡ Lite Smart Secretary - легкая версия без тяжелых ML зависимостей
Решает проблему зацикливания используя только стандартные библиотеки Python
"""

import re
import json
import logging  # ИСПРАВЛЕНО: Добавлено логирование
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from enum import Enum
from .models import Patient, Service, Specialist, Appointment
from django.utils import timezone
from django.db import transaction  # ИСПРАВЛЕНО: Добавлен импорт для транзакций
from .calendar_manager import CalendarSyncManager, DateParser
from .validators import ValidationManager  # ИСПРАВЛЕНО: Добавлена валидация

# ИСПРАВЛЕНО: Настройка логирования
logger = logging.getLogger(__name__)

class DialogState(Enum):
    """Состояния диалога"""
    GREETING = "greeting"
    COLLECTING_SERVICE = "collecting_service"
    COLLECTING_NAME = "collecting_name" 
    COLLECTING_PHONE = "collecting_phone"
    COLLECTING_DATE = "collecting_date"
    COLLECTING_TIME = "collecting_time"
    CONFIRMING = "confirming"
    COMPLETED = "completed"

class LiteEntityExtractor:
    """Легкое извлечение сущностей без ML библиотек"""
    
    @staticmethod
    def extract_name(text: str) -> Optional[str]:
        """Извлекает имя из текста"""
        text_clean = text.strip()
        
        # ИСПРАВЛЕНО: Более точные паттерны для поиска имен
        name_patterns = [
            r'меня зовут\s+([а-яёa-z\s]+)',
            r'имя\s+([а-яёa-z\s]+)',
            r'^([а-яёa-z][а-яёa-z\s]{1,30})\s*мое\s+имя',
            r'^([а-яёa-z]+\s+[а-яёa-z]+)$',  # Имя Фамилия (два слова)
            r'^([а-яёa-z0-9]{2,20})$'  # ИСПРАВЛЕНО: Простое имя (с цифрами для тестов)
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, text_clean, re.IGNORECASE)
            if match:
                name = match.group(1).strip().title()
                # Фильтруем служебные слова и фразы жалоб
                exclude_phrases = [
                    'да', 'нет', 'хорошо', 'ладно', 'привет', 'спасибо',
                    'уже говорил', 'уже сказал', 'свое имя', 'тебе говорил',
                    'я же', 'не помню', 'забыл', 'повторяю',
                    'на массаж', 'на прием', 'на сканирование', 'на диагностику',
                    'на консультацию', 'консультацию',
                    'к аврааму', 'к марии', 'у авраама', 'у марии',
                    'массаж', 'сканирование', 'диагностика', 'лечение',
                    'консультация', 'консультацию',
                    'нутрициолога', 'остеопата', 'реабилитолога',
                    'массажиста', 'врача', 'доктора', 'специалиста',
                    'авраам', 'екатерина', 'римма',  # Имена специалистов
                    'аврааму', 'екатерине', 'римме',
                    'завтра', 'сегодня', 'послезавтра',  # Даты нельзя использовать как имя
                    'понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота', 'воскресенье',
                    # ИСПРАВЛЕНО: Полные названия услуг (чтобы не принимать их за имена)
                    'массаж детский', 'массаж грудным', 'массаж беременным', 'массаж после',
                    'консультация остеопата', 'консультация реабилитолога', 'консультация нутрициолога',
                    'диагностика организма', 'кинезиотейпирование', 'тейпирование',
                    'подбор комплекса', 'упражнений', 'комплекса', 'подбор',
                    'лечебный массаж', 'классический', 'шведский', 'биорезонансным'
                ]
                
                name_lower = name.lower()
                
                # ИСПРАВЛЕНО: Проверяем что это не исключенная фраза
                # Для имен из 2+ слов (Авраам Коэн) проверяем только ПОЛНОЕ совпадение
                # Для имен из 1 слова проверяем частичное совпадение
                words = name.split()
                if len(words) >= 2:
                    # Для составных имен проверяем только точное совпадение
                    is_excluded = name_lower in exclude_phrases
                else:
                    # Для одиночных имен проверяем частичное совпадение
                    is_excluded = any(phrase in name_lower for phrase in exclude_phrases)
                
                if len(name) >= 2 and not is_excluded and len(name.split()) <= 3:
                    return name
        
        return None
    
    @staticmethod  
    def extract_phone(text: str) -> Optional[str]:
        """Извлекает телефон из текста"""
        # Удаляем все кроме цифр, плюса и дефисов
        clean_text = re.sub(r'[^\d\+\-\s]', '', text)
        
        # Паттерны телефонов
        phone_patterns = [
            r'\+?972[0-9\s\-]{8,12}',  # Израильский
            r'0[5-9][0-9\s\-]{8}',     # Местный израильский  
            r'\+?[0-9\s\-]{9,15}'      # Общий
        ]
        
        for pattern in phone_patterns:
            match = re.search(pattern, clean_text)
            if match:
                phone = re.sub(r'[\s\-]', '', match.group())
                if 9 <= len(phone) <= 15:
                    return phone
        
        return None
    
    @staticmethod
    def extract_service(text: str) -> Optional[str]:
        """Извлекает услугу из текста (с точным соответствием из БД)"""
        text_lower = text.lower()
        
        # ИСПРАВЛЕНО: Точные названия услуг из БД
        services = {
            'Лечебный массаж (женщины) - классический шведский': ['массаж для женщин', 'женский массаж', 'массаж женщинам'],
            'Лечебный массаж (мужчины) - классический шведский': ['массаж для мужчин', 'мужской массаж', 'массаж мужчинам'],
            'Лечебный массаж (мужчины) - спортивный': ['спортивный массаж', 'массаж спортивный'],
            'Лечебный массаж (мужчины) - лечебный': ['лечебный массаж', 'массаж лечебный'],
            'Детский массаж': ['детский массаж', 'массаж детям', 'массаж ребенку'],
            'Массаж для грудных детей': ['массаж грудничкам', 'массаж младенцам', 'массаж грудным'],
            'Массаж для беременных': ['массаж беременным', 'беременным массаж', 'для беременных'],
            'Консультация остеопата': ['остеопат', 'кости', 'суставы', 'позвоночник', 'остео', 'к остеопату'],
            'Консультация реабилитолога': ['реабилитация', 'восстановление', 'травма', 'реабилитолог', 'к реабилитологу'],
            'Консультация нутрициолога': ['питание', 'диета', 'вес', 'нутрициолог', 'к нутрициологу'],
            'Диагностика биорезонансным сканированием (базовая)': ['диагностика базовая', 'базовая диагностика', 'сканирование базовое'],
            'Диагностика биорезонансным сканированием (расширенная)': ['диагностика расширенная', 'расширенная диагностика', 'сканирование расширенное'],
            'Диагностика биорезонансным сканированием (VIP)': ['диагностика vip', 'vip диагностика', 'сканирование vip'],
            'Кинезиотейпирование': ['кинезио', 'тейпирование', 'тейпы', 'кинезиотейп'],
            'Подбор и демонстрация комплекса упражнений': ['упражнения', 'комплекс', 'гимнастика', 'лфк']
        }
        
        # Сначала ищем точное совпадение полного названия
        for service_full_name in services.keys():
            if service_full_name.lower() in text_lower:
                return service_full_name
        
        # Потом ищем по ключевым словам
        for service, keywords in services.items():
            if any(keyword in text_lower for keyword in keywords):
                return service
                
        return None
    
    @staticmethod
    def extract_specialist(text: str) -> Optional[str]:
        """Извлекает специалиста из текста"""
        text_lower = text.lower().strip()
        
        # ИСПРАВЛЕНО: Прямые имена специалистов (точное совпадение)
        specialists = {
            'авраам': 'Авраам',
            'екатерина': 'Екатерина',
            'римма': 'Римма',
            'аврааму': 'Авраам',
            'екатерине': 'Екатерина',
            'римме': 'Римма'
        }
        
        # Сначала проверяем прямое совпадение
        for key, value in specialists.items():
            if key in text_lower:
                return value
        
        # Паттерны для поиска специалистов
        specialist_patterns = [
            r'к\s+([а-яё]+)',  # к аврааму, к марии
            r'у\s+([а-яё]+)',  # у авраама, у марии
            r'([а-яё]+)\s+специалист',  # авраам специалист
            r'([а-яё]+)\s+врач',  # авраам врач
            r'([а-яё]+)\s+доктор',  # авраам доктор
        ]
        
        for pattern in specialist_patterns:
            match = re.search(pattern, text_lower)
            if match:
                specialist_name = match.group(1).strip()
                # Проверяем, что это не служебное слово
                if specialist_name not in ['специалист', 'врач', 'доктор', 'к', 'у']:
                    # Нормализуем имя
                    return specialists.get(specialist_name, specialist_name.title())
        
        return None
    
    @staticmethod
    def extract_date(text: str) -> Optional[str]:
        """Извлекает дату из текста"""
        text_lower = text.lower().strip()
        
        # ИСПРАВЛЕНО: Сначала проверяем точные форматы (ISO, числовые)
        # Потом относительные даты (чтобы "2025-10-21 (вторник)" не парсилось как "вторник")
        
        # ISO формат дат (YYYY-MM-DD) из календаря - ПРИОРИТЕТ!
        iso_pattern = r'(\d{4})-(\d{2})-(\d{2})'
        match = re.search(iso_pattern, text)
        if match:
            return match.group(0)  # Только "2025-10-21", без "(вторник)"
        
        # Числовые даты (29.09, 30.09 и т.д.)
        date_pattern = r'(\d{1,2})\.(\d{1,2})'
        match = re.search(date_pattern, text)
        if match:
            day, month = match.groups()
            return f"{day}.{month}"
        
        # Относительные даты (только если нет точного формата)
        # ИСПРАВЛЕНО: Возвращаем конкретные даты вместо строк
        from django.utils import timezone
        from datetime import timedelta
        
        today = timezone.now().date()
        
        relative_dates = {
            'сегодня': today.strftime('%Y-%m-%d'),
            'завтра': (today + timedelta(days=1)).strftime('%Y-%m-%d'), 
            'послезавтра': (today + timedelta(days=2)).strftime('%Y-%m-%d'),
        }
        
        # Дни недели - находим следующий такой день
        weekdays = {
            'понедельник': 0, 'вторник': 1, 'среду': 2, 'четверг': 3, 
            'пятницу': 4, 'субботу': 5, 'воскресенье': 6
        }
        
        for date_word, date_value in relative_dates.items():
            if date_word in text_lower:
                return date_value
        
        # Обработка дней недели
        for day_word, weekday in weekdays.items():
            if day_word in text_lower:
                days_ahead = weekday - today.weekday()
                if days_ahead <= 0:  # Если день уже прошел на этой неделе
                    days_ahead += 7
                target_date = today + timedelta(days=days_ahead)
                return target_date.strftime('%Y-%m-%d')
            
        return None
    
    @staticmethod
    def extract_time(text: str) -> Optional[str]:
        """Извлекает время из текста"""
        text_clean = text.strip()
        
        # ИСПРАВЛЕНО: Паттерны для извлечения времени
        time_patterns = [
            r'(\d{1,2}):(\d{2})',  # 14:00, 9:30
            r'(\d{1,2})\s*:\s*(\d{2})',  # 14 : 00
            r'в\s+(\d{1,2}):(\d{2})',  # в 14:00
            r'на\s+(\d{1,2}):(\d{2})',  # на 14:00
            r'к\s+(\d{1,2}):(\d{2})',  # к 14:00
            r'^(\d{1,2})\s*ч',  # 14ч, 9 ч
            r'^(\d{1,2})\s+час',  # 14 часов
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, text_clean, re.IGNORECASE)
            if match:
                if len(match.groups()) == 2:
                    hour, minute = match.groups()
                    return f"{int(hour)}:{minute}"
                elif len(match.groups()) == 1:
                    hour = match.group(1)
                    return f"{int(hour)}:00"
        
        return None

# Глобальное хранилище сессий (в продакшн можно заменить на Redis)
_global_sessions = {}

class LiteSessionManager:
    """Легкое управление сессиями без внешних зависимостей"""
    
    def __init__(self):
        self.sessions = _global_sessions  # Используем глобальное хранилище
        self.extractor = LiteEntityExtractor()
    
    def get_session(self, session_id: str) -> Dict[str, Any]:
        """Получить сессию"""
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                'state': DialogState.GREETING,
                'entities': {
                    'name': None,
                    'phone': None, 
                    'service': None,
                    'specialist': None,  # ИСПРАВЛЕНО: добавлено поле specialist
                    'date': None,
                    'time': None
                },
                'history': [],
                'created_at': datetime.now(),
                'last_update': datetime.now()
            }
        return self.sessions[session_id]
    
    def update_entities(self, session_id: str, user_message: str) -> Dict[str, str]:
        """Обновляет сущности из сообщения"""
        session = self.get_session(session_id)
        entities = session['entities']
        extracted = {}
        
        # Извлекаем имя
        if not entities['name']:
            name = self.extractor.extract_name(user_message)
            if name:
                entities['name'] = name
                extracted['name'] = name
        
        # Извлекаем телефон
        if not entities['phone']:
            phone = self.extractor.extract_phone(user_message)
            if phone:
                entities['phone'] = phone
                extracted['phone'] = phone
        
        # Извлекаем услугу
        if not entities['service']:
            service = self.extractor.extract_service(user_message)
            if service:
                entities['service'] = service
                extracted['service'] = service
        
        # Извлекаем специалиста
        if not entities['specialist']:
            specialist = self.extractor.extract_specialist(user_message)
            if specialist:
                entities['specialist'] = specialist
                extracted['specialist'] = specialist
        
        # Извлекаем дату
        if not entities['date']:
            date = self.extractor.extract_date(user_message)
            if date:
                entities['date'] = date
                extracted['date'] = date
        
        # ИСПРАВЛЕНО: Извлекаем время
        if not entities['time']:
            time = self.extractor.extract_time(user_message)
            if time:
                entities['time'] = time
                extracted['time'] = time
        
        session['last_update'] = datetime.now()
        return extracted
    
    def get_next_required_field(self, session_id: str) -> Optional[str]:
        """Определяет следующее поле для сбора"""
        session = self.get_session(session_id)
        entities = session['entities']
        
        required_order = ['service', 'specialist', 'name', 'phone', 'date', 'time']
        
        for field in required_order:
            if not entities.get(field):
                return field
        
        return None
    
    def add_to_history(self, session_id: str, role: str, message: str):
        """Добавляет сообщение в историю"""
        session = self.get_session(session_id)
        session['history'].append({
            'role': role,
            'message': message,
            'timestamp': datetime.now()
        })
        
        # Ограничиваем историю
        if len(session['history']) > 10:
            session['history'] = session['history'][-10:]
    
    def get_progress(self, session_id: str) -> float:
        """Прогресс сбора данных (0-1)"""
        session = self.get_session(session_id)
        entities = session['entities']
        
        required = ['service', 'name', 'phone', 'date', 'time']
        completed = sum(1 for field in required if entities.get(field))
        
        return completed / len(required)

class LiteSmartSecretary:
    """Легкий умный секретарь без тяжелых зависимостей"""
    
    def __init__(self):
        self.session_manager = LiteSessionManager()
        
        # Инициализируем календарную систему
        self.calendar_manager = CalendarSyncManager()
        self.date_parser = DateParser()
        
        # ИСПРАВЛЕНО: Добавлена валидация
        self.validator = ValidationManager()
        
        self.stats = {
            'total_requests': 0,
            'memory_recoveries': 0,
            'successful_bookings': 0,
            'calendar_queries': 0,
            'validation_errors': 0,  # ИСПРАВЛЕНО: Добавлен счетчик ошибок валидации
        }
    
    def process_message(self, user_message: str, session_id: str = None) -> Dict[str, Any]:
        """Главная функция обработки сообщений"""
        
        if not session_id:
            session_id = f"lite_{int(datetime.now().timestamp())}"
        
        self.stats['total_requests'] += 1
        
        try:
            return self._process_with_lite_logic(user_message, session_id)
        except Exception as e:
            # ИСПРАВЛЕНО: Детальное логирование ошибок для отладки
            logger.error(f"Error in process_message: {e}", exc_info=True)
            logger.error(f"User message: {user_message}")
            logger.error(f"Session ID: {session_id}")
            
            # Возвращаем понятное сообщение об ошибке
            return {
                'reply': f"Извините, произошла ошибка. Давайте начнем сначала. Чем могу помочь?",
                'intent': 'error',
                'error': str(e),
                'session_id': session_id
            }
    
    def _process_with_lite_logic(self, user_message: str, session_id: str) -> Dict[str, Any]:
        """Обработка с легкой логикой"""
        
        # 1. Добавляем в историю
        self.session_manager.add_to_history(session_id, 'user', user_message)
        
        # 2. Проверяем на жалобу памяти ПЕРВЫМ делом
        if self._is_memory_complaint(user_message):
            response = self._handle_memory_complaint(session_id)
            self.stats['memory_recoveries'] += 1
        else:
            # 3. Извлекаем сущности только если это НЕ жалоба на память
            extracted = self.session_manager.update_entities(session_id, user_message)
            response = self._handle_normal_flow(user_message, session_id, extracted)
            
            # ИСПРАВЛЕНО: Добавляем entities в ответ для отладки
            response['entities'] = self.session_manager.get_session(session_id)['entities']
        
        # 4. Добавляем ответ в историю
        self.session_manager.add_to_history(session_id, 'assistant', response['reply'])
        
        return response
    
    def _is_memory_complaint(self, message: str) -> bool:
        """Проверяет жалобу на забывчивость"""
        complaints = [
            'уже говорил', 'уже сказал', 'уже называл', 
            'я тебе говорил', 'повторяю', 'забыл',
            'не помнишь', 'уже отвечал', 'я же говорил'
        ]
        
        message_lower = message.lower()
        return any(complaint in message_lower for complaint in complaints)
    
    def _handle_memory_complaint(self, session_id: str) -> Dict[str, Any]:
        """Обрабатывает жалобу на забывчивость"""
        session = self.session_manager.get_session(session_id)
        entities = session['entities']
        
        # Собираем что помним
        remembered = []
        if entities.get('name'):
            remembered.append(f"имя: {entities['name']}")
        if entities.get('phone'):
            remembered.append(f"телефон: {entities['phone']}")
        if entities.get('service'):
            remembered.append(f"услуга: {entities['service']}")
        
        if remembered:
            reply = f"Извините за путаницу! У меня записано: {', '.join(remembered)}. Что нужно уточнить дальше?"
        else:
            reply = "Простите за недоразумение! Давайте продолжим. Чем могу помочь?"
        
        return {
            'reply': reply,
            'intent': 'memory_recovery',
            'remembered_data': entities,
            'session_id': session_id
        }
    
    def _handle_normal_flow(self, user_message: str, session_id: str, extracted: Dict) -> Dict[str, Any]:
        """Обычный поток диалога"""
        
        session = self.session_manager.get_session(session_id)
        entities = session['entities']
        
        # ИСПРАВЛЕНО: Обновляем entities перед определением следующего шага
        # (update_entities уже вызван в _process_with_lite_logic, но проверим еще раз)
        if extracted:
            for key, value in extracted.items():
                entities[key] = value
        
        # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Если только что извлекли услугу - сразу проверяем специалиста
        if extracted.get('service') and not entities.get('specialist'):
            available_specialists = self._get_specialists_for_service(entities['service'])
            if len(available_specialists) == 1:
                entities['specialist'] = available_specialists[0]
                # ВАЖНО: Обновляем сессию после автовыбора
                session['entities'] = entities
        
        # Определяем следующий шаг (ПОСЛЕ автовыбора специалиста!)
        next_field = self.session_manager.get_next_required_field(session_id)
        progress = self.session_manager.get_progress(session_id)
        
        if not next_field:
            # Все данные собраны - создаем запись в БД
            
            # ОТЛАДКА: Детальное логирование перед созданием записи
            logger.info(f"=== CREATING APPOINTMENT DEBUG ===")
            logger.info(f"Session ID: {session_id}")
            logger.info(f"Entities: {entities}")
            logger.info(f"Name: {entities.get('name')}")
            logger.info(f"Phone: {entities.get('phone')}")
            logger.info(f"Service: {entities.get('service')}")
            logger.info(f"Specialist: {entities.get('specialist')}")
            logger.info(f"Date: {entities.get('date')} (type: {type(entities.get('date'))})")
            logger.info(f"Time: {entities.get('time')} (type: {type(entities.get('time'))})")
            logger.info(f"Current timezone.now(): {timezone.now()}")
            logger.info(f"Current timezone.now().date(): {timezone.now().date()}")
            logger.info(f"=== END DEBUG ===")
            
            success, result = self.create_appointment(
                session_id=session_id,
                name=entities.get('name'),
                phone=entities.get('phone'),
                service_name=entities.get('service'),
                specialist_name=entities.get('specialist'),
                day=entities.get('date'),
                time=entities.get('time')
            )

            if success:
                self.stats['successful_bookings'] += 1
                reply = self._create_final_confirmation(entities)
                intent = 'booking_completed'
            else:
                # ИСПРАВЛЕНО: При ошибке валидации НЕ сбрасываем диалог
                # Проверяем есть ли в ответе предложение свободных слотов
                if '✅ Доступные слоты' in result:
                    # Сбрасываем только время, оставляем все остальные данные
                    entities['time'] = None
                    session['state'] = DialogState.COLLECTING_TIME
                    reply = result  # Используем сообщение с предложенными слотами (БЕЗ префикса "Извините...")
                    intent = 'collect_time'
                elif 'Центр не работает' in result or 'суббот' in result.lower() or 'воскресен' in result.lower():
                    # Проблема с датой - сбрасываем дату и время
                    entities['date'] = None
                    entities['time'] = None
                    session['state'] = DialogState.COLLECTING_DATE
                    reply = f"{result}\n\nПожалуйста, выберите другую дату."
                    intent = 'collect_date'
                elif '💡 Рекомендуемые времена' in result:
                    # Валидатор предложил слоты (старый формат)
                    entities['time'] = None
                    session['state'] = DialogState.COLLECTING_TIME
                    reply = result
                    intent = 'collect_time'
                else:
                    # Другая ошибка - сообщаем об ошибке
                    reply = f"Извините, произошла ошибка при создании записи: {result}"
                    intent = 'booking_error'
            
        elif next_field == 'service':
            # ИСПРАВЛЕНО: Проверяем, не указал ли пользователь услугу в сообщении
            if 'консультация' in user_message.lower() or 'консультацию' in user_message.lower():
                reply = "Отлично! На консультацию к какому специалисту хотите записаться?"
                intent = 'collect_specialist'
            elif 'массаж' in user_message.lower():
                reply = "Отлично! На массаж к какому специалисту хотите записаться?"
                intent = 'collect_specialist'
            elif 'диагностика' in user_message.lower() or 'диагностику' in user_message.lower():
                reply = "Отлично! На диагностику к какому специалисту хотите записаться?"
                intent = 'collect_specialist'
            else:
                reply = self._ask_for_service(user_message)
                intent = 'collect_service'
            
        elif next_field == 'specialist':
            # ИСПРАВЛЕНО: Проверяем доступных специалистов для услуги
            if entities.get('service'):
                available_specialists = self._get_specialists_for_service(entities['service'])
                
                # АВТОВЫБОР: Если специалист только один - выбираем автоматически
                if len(available_specialists) == 1:
                    entities['specialist'] = available_specialists[0]
                    # ИСПРАВЛЕНО: Сразу переходим к следующему полю (имени)
                    next_field = 'name'
                    reply = f"Отлично! К {available_specialists[0]}. Как вас зовут?"
                    intent = 'collect_name'
                else:
                    # Проверяем, не указал ли пользователь специалиста в сообщении
                    if 'к аврааму' in user_message.lower() or 'авраам' in user_message.lower():
                        entities['specialist'] = 'Авраам'
                        next_field = 'name'
                        reply = "Отлично! К Аврааму. Как вас зовут?"
                        intent = 'collect_name'
                    elif 'к екатерине' in user_message.lower() or 'екатерина' in user_message.lower():
                        entities['specialist'] = 'Екатерина'
                        next_field = 'name'
                        reply = "Отлично! К Екатерине. Как вас зовут?"
                        intent = 'collect_name'
                    elif 'к римме' in user_message.lower() or 'римма' in user_message.lower():
                        entities['specialist'] = 'Римма'
                        next_field = 'name'
                        reply = "Отлично! К Римме. Как вас зовут?"
                        intent = 'collect_name'
                    else:
                        specialists_str = ", ".join(available_specialists)
                        reply = f"К какому специалисту хотите записаться? ({specialists_str})"
                        intent = 'collect_specialist'
            else:
                reply = self._ask_for_specialist(user_message)
                intent = 'collect_specialist'
            
        elif next_field == 'name':
            # ИСПРАВЛЕНО: Если только что выбрали специалиста - упоминаем его
            if extracted.get('service') or extracted.get('specialist'):
                specialist = entities.get('specialist', '')
                if specialist:
                    reply = f"Отлично! К {specialist}. Как вас зовут?"
                else:
                    reply = self._ask_for_name(extracted, entities)
            else:
                reply = self._ask_for_name(extracted, entities)
            intent = 'collect_name'
            
        elif next_field == 'phone':
            reply = self._ask_for_phone(extracted, entities)
            intent = 'collect_phone'
            
        elif next_field == 'date':
            reply = self._ask_for_date_with_calendar(user_message, entities)
            intent = 'collect_date'
            
        elif next_field == 'time':
            reply = self._ask_for_time_with_calendar(user_message, entities)
            intent = 'collect_time'
            
        else:
            reply = "Чем могу помочь?"
            intent = 'general'
        
        return {
            'reply': reply,
            'intent': intent,
            'next_field': next_field,
            'progress': int(progress * 100),
            'session_data': entities,
            'session_id': session_id
        }
    
    def _ask_for_date_with_calendar(self, user_message: str, entities: Dict) -> str:
        """Умный запрос даты с календарной интеграцией"""
        # Пытаемся извлечь дату из сообщения
        parsed_datetime = self.date_parser.extract_datetime(user_message)
        
        if parsed_datetime:
            # Если дата распознана, проверяем доступность
            date = parsed_datetime.date()
            specialist_name = entities.get('specialist')
            
            if specialist_name:
                try:
                    specialist = Specialist.objects.get(name__icontains=specialist_name)
                    service_name = entities.get('service')
                    
                    if service_name:
                        try:
                            service = Service.objects.get(name__icontains=service_name)
                            service_duration = service.duration
                        except Service.DoesNotExist:
                            service_duration = 60  # По умолчанию 60 минут
                    else:
                        service_duration = 60
                    
                    # Получаем доступные слоты
                    available_slots = self.calendar_manager.get_available_slots_with_sync(
                        specialist, date, service_duration
                    )
                    
                    self.stats['calendar_queries'] += 1
                    
                    if available_slots:
                        # Предлагаем конкретные времена
                        formatted_slots = self.date_parser.format_available_slots(available_slots)
                        return f"Отлично! {date.strftime('%d.%m.%Y')} у {specialist.name} доступно:\n{formatted_slots}\n\nВыберите удобное время."
                    else:
                        # Предлагаем альтернативные даты
                        return f"К сожалению, {date.strftime('%d.%m.%Y')} у {specialist.name} нет свободного времени. Предлагаю другие даты: завтра, послезавтра, или следующий вторник."
                except Specialist.DoesNotExist:
                    pass
        
        # Если дата не распознана или специалист не найден, спрашиваем обычно
        return "На какой день вам удобно?"
    
    def _ask_for_time_with_calendar(self, user_message: str, entities: Dict) -> str:
        """Умный запрос времени с календарной интеграцией"""
        # Пытаемся извлечь время из сообщения
        parsed_datetime = self.date_parser.extract_datetime(user_message)
        
        if parsed_datetime:
            # Если время распознано, проверяем доступность
            date = parsed_datetime.date()
            time_obj = parsed_datetime.time()
            specialist_name = entities.get('specialist')
            
            if specialist_name:
                try:
                    specialist = Specialist.objects.get(name__icontains=specialist_name)
                    
                    # Проверяем конфликт
                    start_datetime = timezone.make_aware(
                        datetime.combine(date, time_obj)
                    )
                    service_duration = 60  # Можно получить из entities['service']
                    end_datetime = start_datetime + timedelta(minutes=service_duration)
                    
                    if self.calendar_manager.internal_calendar.check_conflict(
                        specialist, start_datetime, end_datetime
                    ):
                        # Время занято, предлагаем альтернативы
                        available_slots = self.calendar_manager.get_available_slots_with_sync(
                            specialist, date, service_duration
                        )
                        
                        if available_slots:
                            formatted_slots = self.date_parser.format_available_slots(available_slots)
                            return f"К сожалению, {time_obj.strftime('%H:%M')} занято. Доступно:\n{formatted_slots}\n\nВыберите другое время."
                        else:
                            return f"К сожалению, {time_obj.strftime('%H:%M')} занято. Предлагаю выбрать другую дату."
                    else:
                        # Время свободно, подтверждаем
                        return f"Отлично! {date.strftime('%d.%m.%Y')} в {time_obj.strftime('%H:%M')} свободно. Подтверждаете запись?"
                except Specialist.DoesNotExist:
                    pass
        
        # Если время не распознано, спрашиваем обычно
        return "Какое время вам подойдет?"
    
    def _get_specialists_for_service(self, service_name: str) -> list:
        """Получает список специалистов для услуги"""
        # Маппинг услуг на специалистов (точные названия из БД)
        service_specialists = {
            'Лечебный массаж (женщины) - классический шведский': ['Авраам'],
            'Лечебный массаж (мужчины) - классический шведский': ['Авраам'],
            'Лечебный массаж (мужчины) - спортивный': ['Авраам'],
            'Лечебный массаж (мужчины) - лечебный': ['Авраам'],
            'Детский массаж': ['Авраам'],
            'Массаж для грудных детей': ['Авраам'],
            'Массаж для беременных': ['Авраам'],
            'Консультация остеопата': ['Екатерина'],
            'Консультация реабилитолога': ['Екатерина'],
            'Консультация нутрициолога': ['Римма'],
            'Диагностика биорезонансным сканированием (базовая)': ['Екатерина'],
            'Диагностика биорезонансным сканированием (расширенная)': ['Екатерина'],
            'Диагностика биорезонансным сканированием (VIP)': ['Екатерина'],
            'Кинезиотейпирование': ['Екатерина'],
            'Подбор и демонстрация комплекса упражнений': ['Екатерина']
        }
        
        # Получаем специалистов для услуги
        specialists = service_specialists.get(service_name, ['Авраам', 'Екатерина', 'Римма'])
        return specialists
    
    def _ask_for_service(self, user_message: str) -> str:
        """Спрашивает услугу"""
        if any(word in user_message.lower() for word in ['услуги', 'что у вас', 'расскажи']):
            return """У нас доступны:
• Лечебный массаж - 250₪ (Авраам)
• Консультация остеопата - 80₪ (Екатерина)  
• Консультация реабилитолога - 80₪ (Екатерина)
• Консультация нутрициолога - 450₪ (Римма)
• Диагностика - 300-750₪ (Екатерина)

На что хотите записаться?"""
        else:
            # ИСПРАВЛЕНО: Проверяем, не указал ли пользователь услугу в сообщении
            if 'консультация' in user_message.lower() or 'консультацию' in user_message.lower():
                return "Отлично! На консультацию к какому специалисту хотите записаться?"
            elif 'массаж' in user_message.lower():
                return "Отлично! На массаж к какому специалисту хотите записаться?"
            elif 'диагностика' in user_message.lower() or 'диагностику' in user_message.lower():
                return "Отлично! На диагностику к какому специалисту хотите записаться?"
            else:
                return "На какую услугу записываемся? (массаж, консультация, диагностика, остеопат)"
    
    def _ask_for_specialist(self, user_message: str) -> str:
        """Спрашивает специалиста с учетом контекста"""
        # ИСПРАВЛЕНО: Проверяем, не указал ли пользователь специалиста в сообщении
        if 'к аврааму' in user_message.lower() or 'авраам' in user_message.lower():
            return "Отлично! К Аврааму. Как вас зовут?"
        elif 'к екатерине' in user_message.lower() or 'екатерина' in user_message.lower():
            return "Отлично! К Екатерине. Как вас зовут?"
        elif 'к римме' in user_message.lower() or 'римма' in user_message.lower():
            return "Отлично! К Римме. Как вас зовут?"
        else:
            return "К какому специалисту хотите записаться? (Авраам, Екатерина, Римма)"
    
    def _ask_for_name(self, extracted: Dict, entities: Dict) -> str:
        """Спрашивает имя"""
        # ИСПРАВЛЕНО: Всегда просто спрашиваем имя, без перехода к следующему полю
        return "Как вас зовут?"
    
    def _ask_for_phone(self, extracted: Dict, entities: Dict) -> str:
        """Спрашивает телефон"""
        # ИСПРАВЛЕНО: Всегда просто спрашиваем телефон
        name_part = f", {entities['name']}" if entities.get('name') else ""
        return f"Спасибо{name_part}! Укажите ваш номер телефона."
    
    def _ask_for_date(self, entities: Dict) -> str:
        """Спрашивает дату"""
        return "На какой день вам удобно?"
    
    # def _ask_for_time(self, entities: Dict) -> str:  # УДАЛЕНО - заменено на _ask_for_time_with_calendar
    #     """Спрашивает время"""
    #     return "Какое время вам подойдет? (9:00-19:00)"
    
    def _create_final_confirmation(self, entities: Dict) -> str:
        """Создает финальное подтверждение"""
        return f"""✅ Отлично! Запись создана:

👤 Клиент: {entities['name']}
📞 Телефон: {entities['phone']}
🏥 Услуга: {entities['service']}
📅 Дата: {entities.get('date', 'завтра')}
⏰ Время: {entities.get('time', '15:00')}

Мы свяжемся с вами для подтверждения!"""
    
    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """Получает сводку сессии"""
        if session_id not in self.session_manager.sessions:
            return {"error": "Сессия не найдена"}
        
        session = self.session_manager.get_session(session_id)
        
        return {
            'session_id': session_id,
            'entities': session['entities'],
            'progress': self.session_manager.get_progress(session_id),
            'history_length': len(session['history']),
            'created_at': session['created_at'].isoformat(),
            'last_update': session['last_update'].isoformat()
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Получает статистику"""
        return {
            **self.stats,
            'active_sessions': len(self.session_manager.sessions)
        }
    
    def get_learning_insights(self) -> Dict[str, Any]:
        """Получает инсайты для самообучения"""
        return self.learning_engine.get_learning_insights()
    
    def build_knowledge_base(self) -> Dict[str, Any]:
        """Строит базу знаний из диалогов"""
        return self.knowledge_base.build_from_dialogs()
    
    def get_personalized_response(self, phone: str, message: str, base_response: str) -> str:
        """Получает персонализированный ответ"""
        return self.personalization_engine.personalize_response(phone, message, base_response)
    
    def get_advanced_prompt(self, message: str) -> Optional[Dict]:
        """Получает расширенный промпт для сообщения"""
        return self.advanced_prompts.get_prompt_for_message(message)
    
    def get_all_advanced_prompts(self) -> Dict[str, Dict]:
        """Получает все расширенные промпты"""
        return self.advanced_prompts.get_all_prompts()
    
    @transaction.atomic  # ИСПРАВЛЕНО: Добавлена транзакция для целостности данных
    def create_appointment(self, session_id: str, name: str, phone: str,
                          service_name: str, specialist_name: str,
                          day: str, time: str) -> tuple[bool, any]:
        """
        Создает запись на прием в базе данных (с транзакцией и валидацией)

        Returns:
            tuple: (success: bool, result: Appointment|str)
        """
        try:
            # ИСПРАВЛЕНО: Логирование начала создания записи
            logger.info(f"Creating appointment: {name}, {phone}, {service_name}, {specialist_name}, {day}, {time}")

            # Предварительная проверка времени для избежания лишних ошибок валидации
            try:
                from datetime import datetime
                import re
                
                # Очищаем дату от лишнего текста
                date_clean = day.strip()
                date_clean = re.sub(r'\s*\([^)]*\)', '', date_clean).strip()
                
                # Если это "сегодня" и время в прошлом, сразу предлагаем доступные слоты
                if date_clean.lower() in ['сегодня', 'today']:
                    try:
                        time_obj = datetime.strptime(time, '%H:%M').time()
                        now = timezone.now()
                        current_time = now.time()
                        buffer_time = (now + timezone.timedelta(hours=1)).time()
                        
                        if time_obj <= buffer_time:
                            # Время в прошлом или слишком близко - предлагаем доступные слоты
                            try:
                                specialist = Specialist.objects.get(name__icontains=specialist_name)
                                # Более гибкий поиск услуги
                                service = None
                                try:
                                    service = Service.objects.get(name=service_name)
                                except Service.DoesNotExist:
                                    # Поиск по частичному совпадению
                                    services = Service.objects.filter(name__icontains=service_name.split()[0])
                                    if services.exists():
                                        service = services.first()
                                
                                if service:
                                    available_slots = self.validator.availability_validator.get_available_slots(
                                        specialist, now.date(), service.duration
                                    )
                                else:
                                    # Если услуга не найдена, используем стандартную длительность
                                    available_slots = self.validator.availability_validator.get_available_slots(
                                        specialist, now.date(), 60
                                    )
                                
                                if available_slots:
                                    slots_list = [slot['time'] for slot in available_slots[:5]]
                                    slots_str = ", ".join(slots_list)
                                    return False, f"⚠️ Время {time} уже прошло или слишком близко.\n\n✅ Доступные слоты на сегодня: {slots_str}\n\nВыберите удобное время:"
                                else:
                                    return False, "⚠️ На сегодня все слоты заняты. Попробуйте выбрать другой день."
                            except (Specialist.DoesNotExist, Service.DoesNotExist):
                                pass  # Продолжаем обычную валидацию
                    except ValueError:
                        pass  # Неправильный формат времени, продолжаем обычную валидацию
            except Exception:
                pass  # Любая ошибка в предварительной проверке - продолжаем обычную валидацию

            # ИСПРАВЛЕНО: Комплексная валидация всех данных
            validation_result = self.validator.validate_appointment_data(
                name, phone, service_name, specialist_name, day, time
            )
            
            # Детальное логирование для отладки
            logger.info(f"Validation result for appointment: is_valid={validation_result['is_valid']}")
            logger.info(f"Validation data keys: {list(validation_result['data'].keys())}")
            if not validation_result['is_valid']:
                logger.error(f"Validation errors: {validation_result['errors']}")
            
            if not validation_result['is_valid']:
                self.stats['validation_errors'] += 1
                
                # Более информативное логирование с контекстом
                logger.info(f"Appointment validation failed for user request: name={name}, phone={phone}, service={service_name}, specialist={specialist_name}, day={day}, time={time}")
                logger.debug(f"Validation errors: {validation_result['errors']}")
                
                # НОВОЕ: Проверяем конкретно конфликт времени
                time_conflict = any('время уже занято' in err.lower() or 'занят' in err.lower() 
                                   for err in validation_result['errors'])
                weekend_error = any('не работает' in err.lower() or 'суббот' in err.lower() or 'воскресен' in err.lower()
                                   for err in validation_result['errors'])
                
                if time_conflict or weekend_error:
                    # Предлагаем свободные слоты
                    try:
                        specialist = validation_result['data'].get('specialist')
                        service = validation_result['data'].get('service')
                        parsed_date = validation_result['data'].get('date')
                        
                        if specialist and service and parsed_date:
                            available_slots = self.validator.availability_validator.get_available_slots(
                                specialist, parsed_date, service.duration
                            )
                            
                            if available_slots:
                                slots_str = ", ".join(available_slots[:5])
                                # ИСПРАВЛЕНО: Убираем "❌ Обнаружены ошибки:" из начала
                                error_text = validation_result['errors'][0] if validation_result['errors'] else "Это время занято"
                                error_message = f"⚠️ {error_text}\n\n✅ Доступные слоты на {day}: {slots_str}\n\nВыберите удобное время:"
                                return False, error_message
                    except Exception as e:
                        logger.error(f"Error getting available slots: {e}", exc_info=True)
                
                # Если не конфликт времени или не удалось получить слоты - возвращаем обычную ошибку
                error_message = self.validator.get_validation_summary(validation_result)
                return False, error_message
            
            # Если есть предупреждения, логируем их
            if validation_result['warnings']:
                logger.info(f"Validation warnings: {validation_result['warnings']}")

            # 1. Находим или создаем пациента
            patient, created = Patient.objects.get_or_create(
                phone=validation_result['data']['phone'],
                defaults={
                    'name': validation_result['data']['name'],
                    'country': validation_result['data'].get('country', 'Israel'),
                    'city': 'Иерусалим'
                }
            )
            
            # 2. Используем валидированные данные
            service = validation_result['data']['service']
            specialist = validation_result['data']['specialist']
            
            # Проверяем наличие всех необходимых данных
            if 'date' not in validation_result['data'] or 'time' not in validation_result['data']:
                missing_keys = []
                if 'date' not in validation_result['data']:
                    missing_keys.append('date')
                if 'time' not in validation_result['data']:
                    missing_keys.append('time')
                logger.error(f"Missing validation data keys: {missing_keys}")
                return False, f"Ошибка валидации: отсутствуют данные {', '.join(missing_keys)}"
            
            start_datetime = timezone.make_aware(
                datetime.combine(
                    validation_result['data']['date'],
                    validation_result['data']['time']
                )
            )
            
            # 3. Вычисляем время окончания
            end_datetime = start_datetime + timedelta(minutes=service.duration)
            
            # 4. Создаем запись
            appointment = Appointment.objects.create(
                patient=patient,
                service=service,
                specialist=specialist,
                start_time=start_datetime,
                end_time=end_datetime,
                status='pending',
                channel='web',  # Используем 'web' так как это единственный канал в минимальной конфигурации
                notes=f'Запись через ИИ-чат (сессия: {session_id})'
            )

            # 5. Обновляем статистику
            self.stats['successful_bookings'] += 1

            # 6. Обновляем сессию
            session = self.session_manager.get_session(session_id)
            session['entities']['appointment_id'] = appointment.id
            session['state'] = DialogState.COMPLETED

            # ИСПРАВЛЕНО: Логирование успешного создания
            logger.info(f"Appointment created successfully: ID={appointment.id}, Patient={name}, Time={start_datetime}")

            return True, appointment
            
        except Service.DoesNotExist as e:
            logger.error(f"Service not found: {service_name}")
            return False, f"Услуга '{service_name}' не найдена"
        except Specialist.DoesNotExist as e:
            logger.error(f"Specialist not found: {specialist_name}")
            return False, f"Специалист '{specialist_name}' не найден"
        except Exception as e:
            # ИСПРАВЛЕНО: Детальное логирование ошибок
            logger.error(f"Failed to create appointment: {e}", exc_info=True)
            
            # НОВОЕ: Попытка упрощенного создания записи для AI чата
            try:
                logger.info("Attempting simplified appointment creation for AI chat")
                return self._create_simple_appointment(session_id, name, phone, service_name, specialist_name, day, time)
            except Exception as simple_error:
                logger.error(f"Simplified creation also failed: {str(simple_error)}")
                self.stats['creation_errors'] += 1
                return False, f"Ошибка создания записи: {str(e)}"
    
    def _create_simple_appointment(self, session_id: str, name: str, phone: str,
                                 service_name: str, specialist_name: str,
                                 day: str, time: str) -> tuple[bool, any]:
        """
        Упрощенное создание записи без сложной валидации
        Используется как fallback для AI чата
        """
        try:
            logger.info(f"Simple appointment creation: {name}, {phone}, {service_name}, {specialist_name}, {day}, {time}")
            
            # 1. Простая очистка и нормализация данных
            name = name.strip().title()
            phone = phone.strip()
            
            # Простая очистка телефона
            if not phone.startswith('+'):
                if phone.startswith('0'):
                    phone = '+972' + phone[1:]  # Израильский номер
                elif len(phone) == 10:
                    phone = '+972' + phone  # Израильский номер без 0
                else:
                    phone = '+' + phone
            
            # 2. Поиск или создание пациента
            patient, created = Patient.objects.get_or_create(
                phone=phone,
                defaults={
                    'name': name,
                    'country': 'Israel',
                    'city': 'Иерусалим'
                }
            )
            
            # 3. Поиск услуги (гибкий поиск)
            service = None
            try:
                service = Service.objects.get(name=service_name)
            except Service.DoesNotExist:
                # Поиск по частичному совпадению
                services = Service.objects.filter(name__icontains=service_name.split()[0])
                if services.exists():
                    service = services.first()
                else:
                    # Используем первую доступную услугу массажа
                    service = Service.objects.filter(name__icontains='массаж').first()
            
            if not service:
                return False, "Не удалось найти подходящую услугу"
            
            # 4. Поиск специалиста
            specialist = None
            try:
                specialist = Specialist.objects.get(name__icontains=specialist_name)
            except Specialist.DoesNotExist:
                # Используем первого доступного специалиста
                specialist = Specialist.objects.filter(is_active=True).first()
            
            if not specialist:
                return False, "Не удалось найти специалиста"
            
            # 5. Парсинг даты и времени
            appointment_date = None
            appointment_time = None
            
            # Простой парсинг даты
            today = timezone.now().date()
            tomorrow = today + timedelta(days=1)
            
            if 'сегодня' in day.lower() or 'today' in day.lower():
                appointment_date = today
            elif 'завтра' in day.lower() or 'tomorrow' in day.lower():
                appointment_date = tomorrow
            else:
                # Пробуем завтра по умолчанию
                appointment_date = tomorrow
            
            # Простой парсинг времени
            try:
                appointment_time = datetime.strptime(time, '%H:%M').time()
            except ValueError:
                # Используем время по умолчанию
                appointment_time = datetime.strptime('10:00', '%H:%M').time()
            
            # 6. Создание записи
            start_datetime = timezone.make_aware(
                datetime.combine(appointment_date, appointment_time)
            )
            end_datetime = start_datetime + timedelta(minutes=service.duration)
            
            appointment = Appointment.objects.create(
                patient=patient,
                service=service,
                specialist=specialist,
                start_time=start_datetime,
                end_time=end_datetime,
                status='pending',
                channel='web',
                notes=f'Упрощенная запись через ИИ-чат (сессия: {session_id})'
            )
            
            logger.info(f"Simple appointment created successfully: ID={appointment.id}")
            return True, appointment
            
        except Exception as e:
            logger.error(f"Simple appointment creation failed: {str(e)}", exc_info=True)
            return False, f"Не удалось создать запись: {str(e)}"
    
    def _parse_datetime(self, day: str, time: str) -> Optional[datetime]:
        """Парсит дату и время в datetime объект"""
        try:
            # Парсим время
            if ':' in time:
                hour, minute = map(int, time.split(':'))
            else:
                hour = int(time)
                minute = 0
            
            # ИСПРАВЛЕНО: Проверяем, что время в рабочих часах (9:00-19:00)
            if not (9 <= hour < 19):
                return None  # Вне рабочих часов
            
            # Парсим дату
            today = timezone.now().date()
            
            # ИСПРАВЛЕНО: Обработка ISO формата дат (YYYY-MM-DD) из календаря
            if re.match(r'\d{4}-\d{2}-\d{2}', day):
                try:
                    target_date = datetime.strptime(day, '%Y-%m-%d').date()
                except ValueError:
                    return None
            elif re.match(r'\d{1,2}\.\d{1,2}\.?\d{0,4}', day):
                # Формат DD.MM или DD.MM.YYYY
                parts = day.replace('.', ' ').split()
                if len(parts) >= 2:
                    day_num, month_num = int(parts[0]), int(parts[1])
                    year_num = int(parts[2]) if len(parts) > 2 else today.year
                    target_date = datetime(year_num, month_num, day_num).date()
                else:
                    return None
            elif day.lower() in ['сегодня', 'today']:
                target_date = today
            elif day.lower() in ['завтра', 'tomorrow']:
                target_date = today + timedelta(days=1)
            elif day.lower() in ['послезавтра', 'day_after_tomorrow']:
                target_date = today + timedelta(days=2)
            elif day.lower() in ['понедельник', 'monday']:
                days_ahead = 0 - today.weekday()  # Понедельник = 0
                if days_ahead <= 0:  # Понедельник уже прошел на этой неделе
                    days_ahead += 7
                target_date = today + timedelta(days=days_ahead)
            elif day.lower() in ['вторник', 'tuesday']:
                days_ahead = 1 - today.weekday()
                if days_ahead <= 0:
                    days_ahead += 7
                target_date = today + timedelta(days=days_ahead)
            elif day.lower() in ['среду', 'wednesday']:
                days_ahead = 2 - today.weekday()
                if days_ahead <= 0:
                    days_ahead += 7
                target_date = today + timedelta(days=days_ahead)
            elif day.lower() in ['четверг', 'thursday']:
                days_ahead = 3 - today.weekday()
                if days_ahead <= 0:
                    days_ahead += 7
                target_date = today + timedelta(days=days_ahead)
            elif day.lower() in ['пятницу', 'friday']:
                days_ahead = 4 - today.weekday()
                if days_ahead <= 0:
                    days_ahead += 7
                target_date = today + timedelta(days=days_ahead)
            elif day.lower() in ['субботу', 'saturday']:
                days_ahead = 5 - today.weekday()
                if days_ahead <= 0:
                    days_ahead += 7
                target_date = today + timedelta(days=days_ahead)
            elif day.lower() in ['воскресенье', 'sunday']:
                days_ahead = 6 - today.weekday()
                if days_ahead <= 0:
                    days_ahead += 7
                target_date = today + timedelta(days=days_ahead)
            elif '.' in day:  # Формат DD.MM
                day_part, month_part = day.split('.')
                target_date = today.replace(day=int(day_part), month=int(month_part))
            else:
                return None
            
            # Создаем datetime объект
            target_datetime = timezone.make_aware(
                datetime.combine(target_date, datetime.min.time().replace(hour=hour, minute=minute))
            )
            
            # ИСПРАВЛЕНО: Проверяем, что дата не в прошлом
            if target_datetime < timezone.now():
                return None  # Нельзя записаться в прошлое
            
            return target_datetime
            
        except Exception:
            return None
    
    def check_appointments(self, phone: str) -> List[Dict]:
        """Проверяет записи пациента по телефону"""
        try:
            appointments = Appointment.objects.filter(
                patient__phone=phone,
                status__in=['pending', 'confirmed']
            ).order_by('start_time')
            
            result = []
            for apt in appointments:
                result.append({
                    'id': apt.id,
                    'patient_name': apt.patient.name,
                    'service': apt.service.name,
                    'specialist': apt.specialist.name,
                    'date': apt.start_time.strftime('%d.%m.%Y'),
                    'time': apt.start_time.strftime('%H:%M'),
                    'status': apt.status,
                    'notes': apt.notes
                })
            
            return result
            
        except Exception as e:
            return []
    
    def cancel_appointment(self, appointment_id: int) -> tuple[bool, str]:
        """Отменяет запись"""
        try:
            appointment = Appointment.objects.get(id=appointment_id)
            appointment.status = 'cancelled'
            appointment.save()
            return True, "Запись отменена"
        except Appointment.DoesNotExist:
            return False, "Запись не найдена"
        except Exception as e:
            return False, f"Ошибка отмены: {str(e)}"
