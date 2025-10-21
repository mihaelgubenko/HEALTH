from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator


class Patient(models.Model):
    """Модель пациента"""
    name = models.CharField(max_length=100, verbose_name="Имя")
    phone = models.CharField(
        max_length=20,
        verbose_name="Телефон"
    )
    email = models.EmailField(blank=True, null=True, verbose_name="Email")
    country = models.CharField(max_length=50, default="Israel", verbose_name="Страна")
    city = models.CharField(max_length=50, blank=True, null=True, verbose_name="Город")
    notes = models.TextField(blank=True, null=True, verbose_name="Заметки")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Пациент"
        verbose_name_plural = "Пациенты"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.phone})"


class Service(models.Model):
    """Модель услуги"""
    CATALOG_CHOICES = [
        ('A', 'Каталог А (Израиль)'),
        ('B', 'Каталог B (Заграница)'),
    ]

    name = models.CharField(max_length=200, verbose_name="Название услуги")
    description = models.TextField(verbose_name="Описание")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена")
    currency = models.CharField(max_length=3, default="₪", verbose_name="Валюта")
    duration = models.IntegerField(help_text="Длительность в минутах", verbose_name="Длительность")
    catalog = models.CharField(max_length=1, choices=CATALOG_CHOICES, default='A', verbose_name="Каталог")
    is_active = models.BooleanField(default=True, verbose_name="Активна")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Услуга"
        verbose_name_plural = "Услуги"
        ordering = ['catalog', 'name']

    def __str__(self):
        return f"{self.name} - {self.price}{self.currency}"


class Specialist(models.Model):
    """Модель специалиста"""
    name = models.CharField(max_length=100, verbose_name="Имя")
    specialty = models.CharField(max_length=100, verbose_name="Специальность")
    description = models.TextField(blank=True, null=True, verbose_name="Описание")
    working_hours = models.JSONField(
        default=dict,
        help_text="Рабочие часы в формате JSON",
        verbose_name="Рабочие часы"
    )
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Специалист"
        verbose_name_plural = "Специалисты"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} - {self.specialty}"


class Appointment(models.Model):
    """Модель записи на прием"""
    STATUS_CHOICES = [
        ('pending', 'Ожидает подтверждения'),
        ('confirmed', 'Подтверждена'),
        ('cancelled', 'Отменена'),
        ('completed', 'Завершена'),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, verbose_name="Пациент")
    specialist = models.ForeignKey(Specialist, on_delete=models.CASCADE, verbose_name="Специалист")
    service = models.ForeignKey(Service, on_delete=models.CASCADE, verbose_name="Услуга")
    start_time = models.DateTimeField(verbose_name="Время начала")
    end_time = models.DateTimeField(verbose_name="Время окончания")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Статус")
    notes = models.TextField(blank=True, null=True, verbose_name="Заметки")
    channel = models.CharField(max_length=20, default='web', verbose_name="Канал записи")  # web only
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Запись"
        verbose_name_plural = "Записи"
        ordering = ['start_time']

    def __str__(self):
        return f"{self.patient.name} - {self.specialist.name} ({self.start_time.strftime('%d.%m.%Y %H:%M')})"


class Reminder(models.Model):
    """Модель напоминаний о записи"""
    
    REMINDER_TYPE_CHOICES = [
        ('-24h', 'За 24 часа'),
        ('-2h', 'За 2 часа'),
    ]
    
    STATUS_CHOICES = [
        ('scheduled', 'Запланировано'),
        ('sent', 'Отправлено'),
        ('failed', 'Ошибка'),
        ('cancelled', 'Отменено'),
    ]
    
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='reminders', verbose_name='Запись')
    reminder_type = models.CharField(max_length=10, choices=REMINDER_TYPE_CHOICES, verbose_name='Тип напоминания')
    scheduled_at = models.DateTimeField(verbose_name='Время отправки')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled', verbose_name='Статус')
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name='Отправлено')
    error_message = models.TextField(blank=True, verbose_name='Сообщение об ошибке')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    
    class Meta:
        verbose_name = 'Напоминание'
        verbose_name_plural = 'Напоминания'
        ordering = ['scheduled_at']
        indexes = [
            models.Index(fields=['appointment', 'reminder_type']),
            models.Index(fields=['status', 'scheduled_at']),
        ]
    
    def __str__(self):
        return f"Напоминание {self.get_reminder_type_display()} для {self.appointment.patient.name}"


class DialogLog(models.Model):
    """Модель лога диалогов"""
    CHANNEL_CHOICES = [
        ('web', 'Веб-сайт'),
    ]

    # Основные поля для работы с ИИ-секретарем
    session_id = models.CharField(max_length=100, default='unknown', verbose_name="ID сессии")
    user_message = models.TextField(default='', verbose_name="Сообщение пользователя")
    ai_response = models.TextField(default='', verbose_name="Ответ ИИ")
    intent = models.CharField(max_length=50, default='unknown', verbose_name="Намерение")
    service = models.CharField(max_length=200, null=True, blank=True, verbose_name="Услуга")
    specialist = models.CharField(max_length=200, null=True, blank=True, verbose_name="Специалист")
    
    # Дополнительные поля
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default='web', verbose_name="Канал")
    patient = models.ForeignKey(Patient, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Пациент")
    transcript = models.TextField(blank=True, null=True, verbose_name="Транскрипт диалога")
    entities = models.JSONField(default=dict, verbose_name="Извлеченные сущности")
    response = models.TextField(blank=True, null=True, verbose_name="Ответ системы")
    language = models.CharField(max_length=5, default='ru', verbose_name="Язык")
    duration = models.IntegerField(null=True, blank=True, help_text="Длительность в секундах", verbose_name="Длительность")
    applied_playbooks = models.JSONField(default=list, blank=True, verbose_name="Применённые плейбуки")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Лог диалога"
        verbose_name_plural = "Логи диалогов"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.channel} - {self.intent} ({self.created_at.strftime('%d.%m.%Y %H:%M')})"


class ContactMessage(models.Model):
    """Модель для сообщений из формы контактов"""
    name = models.CharField(max_length=100, verbose_name="Имя")
    phone = models.CharField(max_length=20, verbose_name="Телефон")
    email = models.EmailField(blank=True, null=True, verbose_name="Email")
    message = models.TextField(verbose_name="Сообщение")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    is_read = models.BooleanField(default=False, verbose_name="Прочитано")
    
    class Meta:
        verbose_name = "Сообщение контактов"
        verbose_name_plural = "Сообщения контактов"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.created_at.strftime('%d.%m.%Y %H:%M')}"


class FAQ(models.Model):
    """Модель часто задаваемых вопросов"""
    CATEGORY_CHOICES = [
        ('prices', 'Цены'),
        ('address', 'Адрес'),
        ('parking', 'Парковка'),
        ('services', 'Услуги'),
        ('preparation', 'Подготовка к процедуре'),
        ('general', 'Общие вопросы'),
    ]

    question = models.CharField(max_length=300, verbose_name="Вопрос")
    answer = models.TextField(verbose_name="Ответ")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, verbose_name="Категория")
    language = models.CharField(max_length=5, default='ru', verbose_name="Язык")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    order = models.IntegerField(default=0, verbose_name="Порядок")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "FAQ"
        verbose_name_plural = "FAQ"
        ordering = ['category', 'order', 'question']

    def __str__(self):
        return f"{self.question[:50]}..."