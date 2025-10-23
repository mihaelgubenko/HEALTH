"""
Система валидации данных для Smart Secretary
Интеграция с админкой и базой данных
"""

import re
import logging
from typing import Tuple, Optional, Dict, Any, List
from datetime import datetime, time
from django.core.cache import cache
from django.utils import timezone
from .models import Specialist, Service, Appointment
from .datetime_validator import DateTimeValidator, TimezoneManager
from .work_hours import WorkHours

logger = logging.getLogger(__name__)


class NameValidator:
    """Расширенная валидация имен с проверкой языков и реальности"""
    
    # Служебные слова, которые не могут быть именами
    FORBIDDEN_WORDS = {
        'ru': [
            'на', 'к', 'у', 'для', 'запись', 'прием', 'консультация', 
            'массаж', 'диагностика', 'остеопат', 'специалист', 'врач',
            'на массаж', 'на консультацию', 'на диагностику', 'на прием',
            'тест', 'тестовый', 'проверка', 'админ', 'администратор',
            'пользователь', 'клиент', 'пациент', 'человек', 'мужчина', 'женщина',
            'ааа', 'ббб', 'ввв', 'ггг', 'ддд', 'еее', 'жжж', 'ззз',
            'iii', 'ooo', 'uuu', 'yyy', 'xxx', 'zzz', 'aaa', 'bbb', 'ccc',
            'асд', 'фыв', 'йцу', 'qwe', 'asd', 'zxc', 'qaz', 'wsx', 'edc',
            'номер', 'телефон', 'звонок', 'связь', 'контакт', 'информация'
        ],
        'en': [
            'test', 'testing', 'admin', 'administrator', 'user', 'client', 
            'patient', 'person', 'man', 'woman', 'name', 'surname',
            'appointment', 'booking', 'massage', 'consultation', 'doctor',
            'specialist', 'therapy', 'treatment', 'service', 'medical',
            'aaa', 'bbb', 'ccc', 'ddd', 'eee', 'fff', 'ggg', 'hhh',
            'iii', 'jjj', 'kkk', 'lll', 'mmm', 'nnn', 'ooo', 'ppp',
            'qqq', 'rrr', 'sss', 'ttt', 'uuu', 'vvv', 'www', 'xxx', 'yyy', 'zzz',
            'qwe', 'asd', 'zxc', 'qaz', 'wsx', 'edc', 'rfv', 'tgb', 'yhn', 'ujm'
        ],
        'he': [
            'בדיקה', 'טסט', 'מנהל', 'משתמש', 'לקוח', 'חולה', 'איש', 'אישה',
            'תור', 'הזמנה', 'עיסוי', 'יעוץ', 'רופא', 'מומחה', 'טיפול', 'שירות'
        ]
    }
    
    # Популярные имена для проверки реальности
    COMMON_NAMES = {
        'ru': [
            'александр', 'алексей', 'андрей', 'антон', 'артем', 'владимир', 'дмитрий',
            'евгений', 'иван', 'игорь', 'кирилл', 'максим', 'михаил', 'николай',
            'олег', 'павел', 'роман', 'сергей', 'станислав', 'юрий', 'ярослав',
            'анна', 'анастасия', 'валентина', 'виктория', 'галина', 'дарья', 'елена',
            'екатерина', 'ирина', 'кристина', 'людмила', 'марина', 'мария', 'наталья',
            'ольга', 'полина', 'светлана', 'татьяна', 'юлия', 'яна'
        ],
        'en': [
            'alexander', 'andrew', 'anthony', 'benjamin', 'charles', 'christopher', 'daniel',
            'david', 'edward', 'james', 'john', 'joseph', 'matthew', 'michael', 'robert',
            'thomas', 'william', 'alex', 'mike', 'dave', 'tom', 'ben', 'chris', 'dan',
            'amanda', 'amy', 'angela', 'anna', 'ashley', 'barbara', 'betty', 'brenda',
            'carol', 'carolyn', 'cynthia', 'deborah', 'donna', 'dorothy', 'elizabeth',
            'emily', 'helen', 'jennifer', 'jessica', 'karen', 'kimberly', 'linda',
            'lisa', 'maria', 'mary', 'michelle', 'nancy', 'patricia', 'ruth', 'sandra',
            'sarah', 'sharon', 'susan'
        ],
        'he': [
            'אברהם', 'אדם', 'אהרון', 'אורי', 'איתן', 'אלכס', 'אמיר', 'אריה', 'אשר',
            'בנימין', 'גיל', 'דוד', 'דן', 'הלל', 'זאב', 'חיים', 'יוסף', 'יעקב', 'ישראל',
            'כהן', 'לוי', 'מיכאל', 'משה', 'נתן', 'עמוס', 'פטר', 'צבי', 'רון', 'שמואל',
            'אביגיל', 'אדית', 'אורנה', 'איילת', 'אלונה', 'אנה', 'בת שבע', 'גילה', 'דינה',
            'הדס', 'חנה', 'יעל', 'כרמל', 'לאה', 'מירב', 'מרים', 'נעמי', 'עדינה', 'פנינה',
            'רחל', 'רות', 'שרה', 'תמר'
        ]
    }
    
    @staticmethod
    def detect_language(text: str) -> str:
        """Определение языка текста"""
        text_lower = text.lower()
        
        has_cyrillic = bool(re.search(r'[а-яё]', text_lower))
        has_hebrew = bool(re.search(r'[\u0590-\u05FF]', text))
        has_latin = bool(re.search(r'[a-z]', text_lower))
        
        if has_cyrillic:
            return 'ru'
        elif has_hebrew:
            return 'he'
        elif has_latin:
            return 'en'
        else:
            return 'unknown'
    
    @staticmethod
    def normalize_name(name: str) -> str:
        """Нормализация имени"""
        if not name:
            return ""
        
        # Убираем лишние пробелы и приводим к правильному регистру
        name_clean = ' '.join(name.strip().split())
        
        # Для кириллицы и латиницы - первая буква заглавная, остальные строчные
        if re.search(r'[а-яёa-z]', name_clean.lower()):
            name_clean = name_clean.title()
        
        return name_clean
    
    @staticmethod
    def is_realistic_name(name: str, language: str) -> Tuple[bool, str]:
        """Проверка на реалистичность имени"""
        name_lower = name.lower()
        
        # Проверка длины
        if len(name) < 2:
            return False, "Имя слишком короткое"
        
        if len(name) > 50:
            return False, "Имя слишком длинное"
        
        # Проверка на повторяющиеся символы
        if len(set(name_lower)) < 2:
            return False, "Имя не может состоять из одинаковых символов"
        
        # Проверка на последовательности клавиатуры
        keyboard_sequences = [
            'qwerty', 'asdfgh', 'zxcvbn', 'йцукен', 'фывапр', 'ячсмит',
            '123456', 'абвгде', 'abcdef'
        ]
        
        for seq in keyboard_sequences:
            if seq in name_lower or seq[::-1] in name_lower:
                return False, "Имя не может быть последовательностью клавиш"
        
        # Проверка на слишком много согласных или гласных подряд
        if language in ['ru', 'en']:
            vowels = 'аеёиоуыэюяaeiouy'
            consonants = 'бвгджзйклмнпрстфхцчшщbcdfghjklmnpqrstvwxyz'
            
            vowel_count = 0
            consonant_count = 0
            max_vowels = 0
            max_consonants = 0
            
            for char in name_lower:
                if char in vowels:
                    vowel_count += 1
                    consonant_count = 0
                    max_vowels = max(max_vowels, vowel_count)
                elif char in consonants:
                    consonant_count += 1
                    vowel_count = 0
                    max_consonants = max(max_consonants, consonant_count)
                else:
                    vowel_count = 0
                    consonant_count = 0
            
            if max_vowels > 4:
                return False, "Слишком много гласных подряд"
            
            if max_consonants > 5:
                return False, "Слишком много согласных подряд"
        
        return True, "OK"
    
    @classmethod
    def validate_name(cls, name: str) -> Tuple[bool, str]:
        """
        Комплексная валидация имени
        Возвращает: (is_valid, error_message)
        """
        if not name or not name.strip():
            return False, "Имя не может быть пустым"
        
        name_clean = name.strip()
        
        # Проверка минимальной длины
        if len(name_clean) < 2:
            return False, "Имя должно содержать минимум 2 символа"
        
        # Проверка максимальной длины
        if len(name_clean) > 50:
            return False, "Имя не может быть длиннее 50 символов"
        
        # Определение языка
        language = cls.detect_language(name_clean)
        
        if language == 'unknown':
            return False, "Имя должно содержать буквы (русские, английские или иврит)"
        
        # Проверка на смешанные языки
        has_cyrillic = bool(re.search(r'[а-яё]', name_clean.lower()))
        has_hebrew = bool(re.search(r'[\u0590-\u05FF]', name_clean))
        has_latin = bool(re.search(r'[a-z]', name_clean.lower()))
        
        language_count = sum([has_cyrillic, has_hebrew, has_latin])
        
        if language_count > 1:
            return False, "Имя должно быть на одном языке (русский, английский или иврит)"
        
        # Проверка на запрещенные символы
        allowed_chars = r'[а-яёa-z\u0590-\u05FF\s\-\']'
        if not re.match(f'^{allowed_chars}+$', name_clean, re.IGNORECASE):
            return False, "Имя может содержать только буквы, пробелы, дефисы и апострофы"
        
        # Проверка на служебные слова
        name_lower = name_clean.lower()
        forbidden_words = cls.FORBIDDEN_WORDS.get(language, [])
        
        if name_lower in forbidden_words:
            return False, "Это не похоже на имя. Пожалуйста, укажите ваше настоящее имя"
        
        # Проверка на части служебных слов
        for word in forbidden_words:
            if len(word) > 3 and word in name_lower:
                return False, f"Имя не может содержать служебные слова"
        
        # Проверка реалистичности
        realistic, realistic_error = cls.is_realistic_name(name_clean, language)
        if not realistic:
            return False, realistic_error
        
        # Дополнительная проверка для популярных имен (не обязательная, но полезная)
        common_names = cls.COMMON_NAMES.get(language, [])
        name_parts = name_lower.split()
        
        # Проверяем, есть ли хотя бы одна часть имени среди популярных
        has_common_part = False
        for part in name_parts:
            if len(part) >= 3:  # Только значимые части
                for common_name in common_names:
                    if part in common_name or common_name in part:
                        has_common_part = True
                        break
                if has_common_part:
                    break
        
        # Если имя совсем не похоже на популярные, даем предупреждение, но не блокируем
        if not has_common_part and len(name_parts) == 1 and len(name_clean) < 6:
            # Это может быть редкое имя, но мы его пропустим с предупреждением
            pass
        
        return True, "OK"
    
    @classmethod
    def suggest_corrections(cls, name: str) -> list:
        """Предложения по исправлению имени"""
        suggestions = []
        
        if not name or not name.strip():
            return ["Пожалуйста, введите ваше имя"]
        
        name_clean = name.strip()
        language = cls.detect_language(name_clean)
        
        # Нормализация
        normalized = cls.normalize_name(name_clean)
        if normalized != name_clean:
            suggestions.append(f"Возможно, вы имели в виду: {normalized}")
        
        # Предложения популярных имен при похожести
        if language in cls.COMMON_NAMES:
            common_names = cls.COMMON_NAMES[language]
            name_lower = name_clean.lower()
            
            # Поиск похожих имен (простое совпадение первых букв)
            similar_names = []
            for common_name in common_names:
                if (len(name_lower) >= 2 and 
                    common_name.startswith(name_lower[:2])):
                    similar_names.append(common_name.title())
            
            if similar_names:
                suggestions.append(f"Похожие имена: {', '.join(similar_names[:5])}")
        
        return suggestions


class PhoneValidator:
    """Расширенная валидация телефонов по странам с детальными проверками"""
    
    # Коды операторов по странам
    COUNTRY_OPERATORS = {
        'IL': {
            'mobile_prefixes': ['50', '51', '52', '53', '54', '55', '56', '57', '58', '59'],
            'landline_prefixes': ['02', '03', '04', '08', '09'],
            'special_prefixes': ['1700', '1800', '1801', '1802', '1803'],
            'length': 9,  # без кода страны
            'country_code': '+972',
            'local_prefix': '0'
        },
        'RU': {
            'mobile_prefixes': ['900', '901', '902', '903', '904', '905', '906', '908', '909', 
                              '910', '911', '912', '913', '914', '915', '916', '917', '918', '919',
                              '920', '921', '922', '923', '924', '925', '926', '927', '928', '929',
                              '930', '931', '932', '933', '934', '936', '937', '938', '939',
                              '950', '951', '952', '953', '954', '955', '956', '958', '960', '961',
                              '962', '963', '964', '965', '966', '967', '968', '969', '970', '971',
                              '977', '978', '980', '981', '982', '983', '984', '985', '986', '987', '988', '989',
                              '991', '992', '993', '994', '995', '996', '997', '999'],
            'length': 10,  # без кода страны
            'country_code': '+7',
            'local_prefix': '8'
        },
        'UA': {
            'mobile_prefixes': ['50', '63', '66', '67', '68', '73', '91', '92', '93', '94', '95', '96', '97', '98', '99'],
            'landline_prefixes': ['32', '33', '34', '35', '36', '37', '38', '41', '43', '44', '45', '46', '47', '48', '49'],
            'length': 9,  # без кода страны
            'country_code': '+380',
            'local_prefix': '0'
        },
        'US': {
            'mobile_prefixes': [],  # В США нет разделения на мобильные/стационарные по префиксу
            'landline_prefixes': [],
            'length': 10,  # без кода страны
            'country_code': '+1',
            'local_prefix': '1'
        }
    }
    
    @staticmethod
    def clean_phone(phone: str) -> str:
        """Очистка номера от лишних символов"""
        if not phone:
            return ""
        
        # Убираем все кроме цифр и +
        cleaned = re.sub(r'[^\d+]', '', phone.strip())
        
        # Убираем множественные + в начале
        if cleaned.startswith('++'):
            cleaned = '+' + cleaned.lstrip('+')
        
        return cleaned
    
    @staticmethod
    def detect_country_by_phone(phone_clean: str) -> Tuple[str, str]:
        """
        Упрощенное определение страны по номеру телефона
        Возвращает: (country_code, remaining_digits)
        """
        # Израиль
        if phone_clean.startswith('+972'):
            return 'IL', phone_clean[4:]
        elif phone_clean.startswith('972'):
            return 'IL', phone_clean[3:]
        elif phone_clean.startswith('0') and len(phone_clean) >= 9:
            return 'IL', phone_clean[1:]
        elif len(phone_clean) == 9:
            return 'IL', phone_clean
        
        # Россия
        elif phone_clean.startswith('+7'):
            return 'RU', phone_clean[2:]
        elif phone_clean.startswith('7') and len(phone_clean) == 11:
            return 'RU', phone_clean[1:]
        elif phone_clean.startswith('8') and len(phone_clean) == 11:
            return 'RU', phone_clean[1:]
        elif len(phone_clean) == 10:
            return 'RU', phone_clean
        
        # Украина
        elif phone_clean.startswith('+380'):
            return 'UA', phone_clean[4:]
        elif phone_clean.startswith('380'):
            return 'UA', phone_clean[3:]
        
        # США
        elif phone_clean.startswith('+1'):
            return 'US', phone_clean[2:]
        elif phone_clean.startswith('1') and len(phone_clean) == 11:
            return 'US', phone_clean[1:]
        
        # Если не удалось точно определить, пробуем по длине
        # 10 цифр могут быть: Россия (без кода), США (без кода), Израиль (невероятно)
        # 9 цифр могут быть: Израиль (без 0), Украина (без 0)
        elif len(phone_clean) == 10:
            # Предполагаем США (или Россия без кода)
            return 'US', phone_clean
        elif len(phone_clean) == 9:
            # Предполагаем Израиль
            return 'IL', phone_clean
        
        # Если совсем не можем определить - возвращаем как есть без страны
        # Валидация будет работать в упрощенном режиме
        return 'IL', phone_clean  # По умолчанию Израиль (основная страна клиники)
    
    @staticmethod
    def validate_phone_by_country(country: str, digits: str) -> Tuple[bool, str]:
        """Упрощенная валидация номера для конкретной страны - только базовые проверки"""
        if country not in PhoneValidator.COUNTRY_OPERATORS:
            return False, f"Неподдерживаемая страна: {country}"
        
        country_info = PhoneValidator.COUNTRY_OPERATORS[country]
        expected_length = country_info['length']
        
        # Проверка длины - основная проверка
        if len(digits) != expected_length:
            return False, f"Неверная длина номера для {country}. Ожидается {expected_length} цифр, получено {len(digits)}"
        
        # Упрощенные проверки - только очевидно неверные номера
        if country == 'IL':
            # Для Израиля - принимаем все номера правильной длины
            # Убираем строгую проверку кодов операторов
            pass
        
        elif country == 'RU':
            # Для России - проверяем что начинается с 9 (мобильный) или 4/8 (регион)
            if not (digits[0] in ['9', '4', '8'] or digits[:3] in ['495', '496', '498', '499']):
                return False, "Российский номер должен начинаться с 9 (мобильный) или кода региона"
        
        elif country == 'UA':
            # Для Украины - принимаем все номера правильной длины
            # Убираем строгую проверку кодов операторов
            pass
        
        elif country == 'US':
            # Для США проверяем что первая цифра не 0 или 1
            if digits[0] in ['0', '1']:
                return False, "Номер в США не может начинаться с 0 или 1"
            
            # Проверяем что четвертая цифра не 0 или 1
            if len(digits) >= 4 and digits[3] in ['0', '1']:
                return False, "Неверный формат номера США"
        
        return True, "OK"
    
    @staticmethod
    def format_phone(country: str, digits: str) -> str:
        """Форматирование номера в международный формат"""
        if country not in PhoneValidator.COUNTRY_OPERATORS:
            return digits
        
        country_code = PhoneValidator.COUNTRY_OPERATORS[country]['country_code']
        return f"{country_code}{digits}"
    
    @staticmethod
    def get_phone_info(phone: str) -> Dict[str, Any]:
        """Получение детальной информации о номере"""
        phone_clean = PhoneValidator.clean_phone(phone)
        country, digits = PhoneValidator.detect_country_by_phone(phone_clean)
        
        info = {
            'original': phone,
            'cleaned': phone_clean,
            'country': country,
            'digits': digits,
            'is_valid': False,
            'formatted': '',
            'type': 'unknown',
            'operator': 'unknown',
            'errors': []
        }
        
        if country == 'UNKNOWN':
            info['errors'].append("Не удалось определить страну")
            return info
        
        # Валидация для страны
        is_valid, error = PhoneValidator.validate_phone_by_country(country, digits)
        info['is_valid'] = is_valid
        
        if not is_valid:
            info['errors'].append(error)
            return info
        
        # Форматирование
        info['formatted'] = PhoneValidator.format_phone(country, digits)
        
        # Определение типа (мобильный/стационарный)
        country_info = PhoneValidator.COUNTRY_OPERATORS[country]
        
        if country in ['IL', 'UA']:
            prefix = digits[:2]
            if prefix in country_info['mobile_prefixes']:
                info['type'] = 'mobile'
            elif prefix in country_info['landline_prefixes']:
                info['type'] = 'landline'
        elif country == 'RU':
            prefix = digits[:3]
            if prefix in country_info['mobile_prefixes']:
                info['type'] = 'mobile'
            else:
                info['type'] = 'landline'
        elif country == 'US':
            info['type'] = 'mobile_or_landline'  # В США нельзя различить по номеру
        
        return info
    
    @classmethod
    def validate_phone(cls, phone: str) -> Tuple[bool, str, str]:
        """
        Упрощенная валидация телефона - только базовая очистка
        Возвращает: (is_valid, country_code, formatted_phone)
        """
        if not phone or not phone.strip():
            return False, '', ''
        
        # Только базовая очистка
        cleaned = cls.clean_phone(phone)
        
        # Минимальная длина
        if len(cleaned) < 7:
            return False, '', cleaned
        
        # Определяем страну (упрощенно)
        country, remaining = cls.detect_country_by_phone(cleaned)
        
        if not country:
            # Если не определили страну, считаем израильским
            country = 'IL'
            remaining = cleaned
        
        # Форматируем номер
        country_config = cls.COUNTRY_OPERATORS.get(country, {})
        country_code = country_config.get('country_code', '+972')
        formatted = f"{country_code}{remaining}"
        
        return True, country, formatted
    
    @classmethod
    def suggest_corrections(cls, phone: str) -> List[str]:
        """Предложения по исправлению номера"""
        suggestions = []
        
        if not phone or not phone.strip():
            return ["Пожалуйста, введите номер телефона"]
        
        phone_clean = cls.clean_phone(phone)
        
        # Если номер слишком короткий, предлагаем добавить код страны
        if len(phone_clean) < 9:
            suggestions.append("Номер слишком короткий. Добавьте код страны (+972, +7, +380, +1)")
        
        # Если номер начинается с цифр без +, предлагаем варианты
        if phone_clean.isdigit():
            if len(phone_clean) == 9:
                suggestions.append(f"Возможно: +972{phone_clean} (Израиль)")
            elif len(phone_clean) == 10:
                suggestions.append(f"Возможно: +7{phone_clean} (Россия)")
                suggestions.append(f"Возможно: +380{phone_clean[1:]} (Украина, если начинается с 0)")
                suggestions.append(f"Возможно: +1{phone_clean} (США)")
            elif len(phone_clean) == 11:
                if phone_clean.startswith('7'):
                    suggestions.append(f"Возможно: +{phone_clean} (Россия)")
                elif phone_clean.startswith('1'):
                    suggestions.append(f"Возможно: +{phone_clean} (США)")
        
        # Проверяем распространенные ошибки
        if phone_clean.startswith('00'):
            # Двойной международный префикс
            corrected = '+' + phone_clean[2:]
            suggestions.append(f"Уберите лишний 0: {corrected}")
        
        if phone_clean.count('+') > 1:
            # Множественные +
            corrected = '+' + phone_clean.replace('+', '')
            suggestions.append(f"Уберите лишние +: {corrected}")
        
        return suggestions
    
    @classmethod
    def get_example_formats(cls) -> Dict[str, List[str]]:
        """Примеры правильных форматов для каждой страны"""
        return {
            'IL': ['+972501234567', '0501234567', '501234567'],
            'RU': ['+79123456789', '89123456789', '79123456789'],
            'UA': ['+380501234567', '0501234567'],
            'US': ['+12345678901', '12345678901']
        }


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


class ConflictValidator:
    """Валидация конфликтов записей и дублирования"""
    
    @staticmethod
    def check_appointment_conflicts(specialist: Specialist, start_datetime: datetime, 
                                  end_datetime: datetime, exclude_appointment_id: Optional[int] = None) -> Tuple[bool, List[str]]:
        """
        Проверка конфликтов записей
        Возвращает: (has_conflicts, conflict_descriptions)
        """
        conflicts = []
        
        # Базовый запрос для поиска конфликтов
        conflict_query = Appointment.objects.filter(
            specialist=specialist,
            status__in=['pending', 'confirmed'],
            start_time__lt=end_datetime,
            end_time__gt=start_datetime
        )
        
        # Исключаем текущую запись (при редактировании)
        if exclude_appointment_id:
            conflict_query = conflict_query.exclude(id=exclude_appointment_id)
        
        conflicting_appointments = conflict_query.select_related('patient', 'service')
        
        for appointment in conflicting_appointments:
            conflict_desc = (
                f"Конфликт с записью: {appointment.patient.name} "
                f"({appointment.service.name}) "
                f"с {appointment.start_time.strftime('%H:%M')} "
                f"до {appointment.end_time.strftime('%H:%M')}"
            )
            conflicts.append(conflict_desc)
        
        return len(conflicts) > 0, conflicts
    
    @staticmethod
    def check_patient_double_booking(patient_phone: str, start_datetime: datetime, 
                                   end_datetime: datetime, exclude_appointment_id: Optional[int] = None) -> Tuple[bool, str]:
        """
        Проверка двойного бронирования для одного пациента (КОНФЛИКТ времени)
        Блокирует создание записи если у пациента уже есть запись на это же время
        """
        from .models import Patient
        
        try:
            # Ищем пациента по телефону
            patients = Patient.objects.filter(phone=patient_phone)
            if not patients.exists():
                return False, ""
            
            # Проверяем записи пациента на это время
            conflict_query = Appointment.objects.filter(
                patient__in=patients,
                status__in=['pending', 'confirmed'],
                start_time__lt=end_datetime,
                end_time__gt=start_datetime
            )
            
            if exclude_appointment_id:
                conflict_query = conflict_query.exclude(id=exclude_appointment_id)
            
            conflicting_appointments = conflict_query.select_related('specialist', 'service')
            
            if conflicting_appointments.exists():
                appointment = conflicting_appointments.first()
                return True, (
                    f"У вас уже есть запись на это время: "
                    f"{appointment.specialist.name} ({appointment.service.name}) "
                    f"с {appointment.start_time.strftime('%H:%M')} "
                    f"до {appointment.end_time.strftime('%H:%M')}"
                )
            
            return False, ""
            
        except Exception as e:
            logger.error(f"Error checking patient double booking: {e}")
            return False, ""
    
    @staticmethod
    def get_patient_existing_appointments(patient_phone: str, 
                                        exclude_appointment_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Получить все существующие записи пациента (для УВЕДОМЛЕНИЙ, не блокирует)
        Возвращает список записей с деталями: дата, время, специалист, услуга
        """
        from .models import Patient
        
        try:
            # Ищем пациента по телефону
            patients = Patient.objects.filter(phone=patient_phone)
            if not patients.exists():
                return []
            
            # Получаем все активные записи пациента
            appointments_query = Appointment.objects.filter(
                patient__in=patients,
                status__in=['pending', 'confirmed']
            ).select_related('specialist', 'service').order_by('start_time')
            
            if exclude_appointment_id:
                appointments_query = appointments_query.exclude(id=exclude_appointment_id)
            
            # Формируем список записей
            existing_appointments = []
            for appointment in appointments_query:
                existing_appointments.append({
                    'id': appointment.id,
                    'date': appointment.start_time.date(),
                    'date_str': appointment.start_time.strftime('%d.%m.%Y'),
                    'time': appointment.start_time.strftime('%H:%M'),
                    'specialist': appointment.specialist.name,
                    'service': appointment.service.name,
                    'status': appointment.status,
                    'start_datetime': appointment.start_time,
                    'end_datetime': appointment.end_time
                })
            
            return existing_appointments
            
        except Exception as e:
            logger.error(f"Error getting patient existing appointments: {e}")
            return []
    
    @staticmethod
    def find_alternative_slots(specialist: Specialist, preferred_date: datetime.date, 
                             duration: int, num_alternatives: int = 5) -> List[Dict[str, Any]]:
        """Поиск альтернативных свободных слотов"""
        alternatives = []
        
        # Используем новый DateTimeValidator для получения слотов
        datetime_validator = DateTimeValidator()
        
        # Проверяем несколько дней вперед
        for days_offset in range(7):  # Неделя вперед
            check_date = preferred_date + timezone.timedelta(days=days_offset)
            
            # Получаем доступные слоты на дату
            available_slots = datetime_validator.get_available_time_slots(check_date, duration)
            
            for slot in available_slots:
                slot_datetime = slot['datetime']
                
                # Проверяем конфликты с существующими записями
                end_datetime = slot_datetime + timezone.timedelta(minutes=duration)
                has_conflicts, _ = ConflictValidator.check_appointment_conflicts(
                    specialist, slot_datetime, end_datetime
                )
                
                if not has_conflicts:
                    # Убеждаемся, что time существует и не пустой
                    slot_time = slot.get('time')
                    if not slot_time:
                        slot_time = slot_datetime.strftime('%H:%M')
                    
                    alternatives.append({
                        'date': check_date,
                        'time': slot_time,
                        'datetime': slot_datetime,
                        'date_str': check_date.strftime('%d.%m.%Y'),
                        'weekday': check_date.strftime('%A')
                    })
                    
                    if len(alternatives) >= num_alternatives:
                        return alternatives
        
        return alternatives


class AvailabilityValidator:
    """Валидация доступности времени с интеграцией с админкой и новой системой валидации"""
    
    def __init__(self, country: str = 'IL'):
        self.datetime_validator = DateTimeValidator(country)
        self.conflict_validator = ConflictValidator()
    
    def check_availability(self, specialist: Specialist, date: datetime.date, 
                          time_obj: datetime.time, duration: int = 60) -> Tuple[bool, str]:
        """
        Проверка доступности времени с учетом всех факторов
        Возвращает: (is_available, error_message)
        """
        try:
            # 1. Валидация даты и времени через новую систему
            date_str = date.strftime('%Y-%m-%d')
            time_str = time_obj.strftime('%H:%M')
            
            datetime_result = self.datetime_validator.validate_datetime(date_str, time_str)
            
            if not datetime_result['is_valid']:
                return False, "; ".join(datetime_result['errors'])
            
            # 2. Проверка конфликтов записей
            start_datetime = datetime_result['parsed_datetime']
            end_datetime = start_datetime + timezone.timedelta(minutes=duration)
            
            has_conflicts, conflict_descriptions = self.conflict_validator.check_appointment_conflicts(
                specialist, start_datetime, end_datetime
            )
            
            if has_conflicts:
                return False, conflict_descriptions[0]  # Возвращаем первый конфликт
            
            logger.info(f"Time slot available: {specialist.name} on {date} at {time_obj}")
            return True, "OK"
            
        except Exception as e:
            logger.error(f"Error checking availability: {e}")
            return False, f"Ошибка проверки доступности: {str(e)}"
    
    def get_available_slots(self, specialist: Specialist, date: datetime.date, 
                          service_duration: int = 60) -> List[Dict[str, Any]]:
        """
        Получение доступных слотов времени для специалиста на дату
        """
        try:
            # Кэширование на 5 минут для производительности
            cache_key = f"slots_v2_{specialist.id}_{date}_{service_duration}"
            cached_slots = cache.get(cache_key)
            
            if cached_slots:
                return cached_slots
            
            # Получаем базовые слоты через новую систему валидации
            base_slots = self.datetime_validator.get_available_time_slots(date, service_duration)
            
            # Фильтруем слоты по конфликтам с записями
            available_slots = []
            
            for slot in base_slots:
                slot_datetime = slot['datetime']
                end_datetime = slot_datetime + timezone.timedelta(minutes=service_duration)
                
                # Проверяем конфликты
                has_conflicts, _ = self.conflict_validator.check_appointment_conflicts(
                    specialist, slot_datetime, end_datetime
                )
                
                if not has_conflicts:
                    available_slots.append({
                        'time': slot['time'],
                        'datetime': slot_datetime.isoformat(),
                        'available': True,
                        'duration': service_duration
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
    
    def __init__(self, country: str = 'IL'):
        self.country = country
        self.name_validator = NameValidator()
        self.phone_validator = PhoneValidator()
        self.service_validator = ServiceValidator()
        self.availability_validator = AvailabilityValidator(country)
        self.datetime_validator = DateTimeValidator(country)
        self.conflict_validator = ConflictValidator()
        
        # Кэш для ускорения повторных валидаций
        self._validation_cache = {}
    
    def validate_appointment_data(self, name: str, phone: str, service_name: str, 
                               specialist_name: str, date: str, time_str: str, 
                               exclude_appointment_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Комплексная валидация всех данных записи с проверкой конфликтов
        Возвращает результат валидации с детальной информацией
        """
        result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'data': {},
            'suggestions': [],
            'alternatives': []
        }
        
        # 1. Валидация имени
        name_valid, name_error = self.name_validator.validate_name(name)
        if not name_valid:
            result['is_valid'] = False
            result['errors'].append(f"Имя: {name_error}")
            # Добавляем предложения по исправлению имени
            name_suggestions = self.name_validator.suggest_corrections(name)
            if name_suggestions:
                result['suggestions'].extend(name_suggestions)
        else:
            # Нормализуем имя
            normalized_name = self.name_validator.normalize_name(name)
            result['data']['name'] = normalized_name
            if normalized_name != name.strip():
                result['warnings'].append(f"Имя нормализовано: {normalized_name}")
        
        # 2. Валидация телефона (упрощенная - не блокирует создание записи)
        phone_valid, country, formatted_phone = self.phone_validator.validate_phone(phone)
        if not phone_valid:
            # Не блокируем создание записи, только предупреждаем
            result['warnings'].append(f"Телефон может быть некорректным: {formatted_phone}")
            # Используем исходный номер как есть
            result['data']['phone'] = phone.strip()
            result['data']['country'] = 'IL'  # По умолчанию
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
        if specialist_obj and service_obj and date and time_str:
            # Используем новую систему валидации даты и времени
            datetime_result = self.datetime_validator.validate_datetime(date, time_str)
            
            if not datetime_result['is_valid']:
                result['is_valid'] = False
                result['errors'].extend(datetime_result['errors'])
                
                # Предлагаем альтернативные даты
                if datetime_result['parsed_date']:
                    alternatives = self.datetime_validator.suggest_alternative_dates(
                        datetime_result['parsed_date']
                    )
                    result['alternatives'] = alternatives
            else:
                parsed_date = datetime_result['parsed_date']
                parsed_time = datetime_result['parsed_time']
                parsed_datetime = datetime_result['parsed_datetime']
                
                # 6. Проверка доступности времени
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
                    
                    # Предлагаем альтернативные даты со свободными слотами
                    alternatives = self.conflict_validator.find_alternative_slots(
                        specialist_obj, parsed_date, duration
                    )
                    result['alternatives'] = alternatives
                else:
                    # 7. Проверка двойного бронирования пациента
                    if formatted_phone:
                        end_datetime = parsed_datetime + timezone.timedelta(minutes=duration)
                        has_double_booking, double_booking_error = self.conflict_validator.check_patient_double_booking(
                            formatted_phone, parsed_datetime, end_datetime, exclude_appointment_id
                        )
                        
                        if has_double_booking:
                            result['is_valid'] = False
                            result['errors'].append(f"Конфликт записей: {double_booking_error}")
                    
                    # Если все проверки пройдены, сохраняем данные
                    if result['is_valid']:
                        result['data']['date'] = parsed_date
                        result['data']['time'] = parsed_time
                        result['data']['datetime'] = parsed_datetime
                        result['data']['duration'] = duration
        
        # Логирование результата валидации
        if result['is_valid']:
            logger.debug(f"Validation successful for: {name}, {phone}")
        else:
            logger.debug(f"Validation failed: {result['errors']}")
        
        return result
    
    def validate_appointment_edit(self, appointment_id: int, name: str, phone: str, 
                                service_name: str, specialist_name: str, 
                                date: str, time_str: str) -> Dict[str, Any]:
        """
        Валидация при редактировании записи (исключает текущую запись из проверки конфликтов)
        """
        return self.validate_appointment_data(
            name, phone, service_name, specialist_name, date, time_str, 
            exclude_appointment_id=appointment_id
        )
    
    def get_validation_summary(self, validation_result: Dict[str, Any]) -> str:
        """
        Генерирует упрощенное сообщение о результатах валидации
        """
        if validation_result['is_valid']:
            return "✅ Все данные корректны!"
        else:
            # Упрощенные сообщения об ошибках
            friendly_errors = []
            for error in validation_result['errors']:
                if 'телефон' in error.lower():
                    friendly_errors.append("📞 Проверьте номер телефона")
                elif 'время' in error.lower():
                    friendly_errors.append("⏰ Время недоступно")
                elif 'специалист' in error.lower():
                    friendly_errors.append("👨‍⚕️ Специалист не найден")
                elif 'услуга' in error.lower():
                    friendly_errors.append("🏥 Услуга не найдена")
                elif 'имя' in error.lower():
                    friendly_errors.append("👤 Проверьте имя")
                else:
                    friendly_errors.append("⚠️ Есть ошибка в данных")
            
            # Показываем только первую ошибку
            if friendly_errors:
                return f"{friendly_errors[0]}\n\nЧто хотите исправить?"
            else:
                return "⚠️ Есть ошибка в данных\n\nЧто хотите исправить?"
    
    def get_detailed_validation_report(self, validation_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Генерирует детальный отчет о валидации для отладки
        """
        return {
            'summary': self.get_validation_summary(validation_result),
            'is_valid': validation_result['is_valid'],
            'errors_count': len(validation_result['errors']),
            'warnings_count': len(validation_result['warnings']),
            'suggestions_count': len(validation_result['suggestions']),
            'alternatives_count': len(validation_result['alternatives']),
            'validated_data': validation_result['data'],
            'country': self.country,
            'timestamp': timezone.now().isoformat()
        }
