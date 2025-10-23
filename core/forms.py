from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Appointment, Service, Specialist


class AppointmentForm(forms.ModelForm):
    """Форма записи на прием"""
    
    name = forms.CharField(
        max_length=100,
        label='Ваше имя',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите ваше имя',
            'required': True,
            'minlength': '2',
            'maxlength': '100'
        })
    )
    
    phone = forms.CharField(
        max_length=20,
        label='Телефон',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите ваш номер телефона',
            'required': True,
            'type': 'tel',
            'pattern': r'[\+]?[0-9\s\-\(\)]{7,20}',
            'title': 'Введите номер телефона в международном формате'
        })
    )
    
    email = forms.EmailField(
        required=False,
        label='Email (необязательно)',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'your@email.com',
            'type': 'email'
        })
    )
    
    preferred_date = forms.DateField(
        label='Предпочитаемая дата',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'min': timezone.now().date().strftime('%Y-%m-%d'),
            'required': True
        })
    )
    
    preferred_time = forms.ChoiceField(
        label='Предпочитаемое время',
        choices=[],
        widget=forms.Select(attrs={
            'class': 'form-control',
            'required': True
        })
    )
    
    notes = forms.CharField(
        required=False,
        label='Дополнительная информация',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Опишите ваши симптомы или пожелания...'
        })
    )

    class Meta:
        model = Appointment
        fields = ['service', 'specialist']
        widgets = {
            'service': forms.Select(attrs={'class': 'form-control', 'required': True}),
            'specialist': forms.Select(attrs={'class': 'form-control', 'required': True}),
        }
        labels = {
            'service': 'Услуга',
            'specialist': 'Специалист',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Заполняем услуги
        self.fields['service'].queryset = Service.objects.filter(is_active=True, catalog='A')
        
        # Заполняем специалистов
        self.fields['specialist'].queryset = Specialist.objects.filter(is_active=True)
        
        # Заполняем временные слоты
        time_choices = [('', 'Выберите время')]
        
        # Генерируем все доступные слоты с 10:00 до 19:00
        for hour in range(10, 19):
            for minute in [0, 30]:
                time_str = f'{hour:02d}:{minute:02d}'
                time_choices.append((time_str, time_str))
        
        self.fields['preferred_time'].choices = time_choices

    def clean_phone(self):
        phone = self.cleaned_data['phone']
        # Простая очистка - убираем только лишние пробелы
        return phone.strip()

    def clean_preferred_date(self):
        date = self.cleaned_data['preferred_date']
        # Используем локальное время пользователя (Israel timezone)
        today = timezone.now().date()
        if date < today:
            raise ValidationError('Дата не может быть в прошлом')
        return date
    
    def clean(self):
        cleaned_data = super().clean()
        preferred_date = cleaned_data.get('preferred_date')
        preferred_time = cleaned_data.get('preferred_time')
        specialist = cleaned_data.get('specialist')
        service = cleaned_data.get('service')
        
        if preferred_date and preferred_time and specialist and service:
            # Проверяем, что время не в прошлом для сегодняшней даты
            now = timezone.now()
            today = now.date()
            
            if preferred_date == today:
                try:
                    slot_time = datetime.strptime(preferred_time, '%H:%M').time()
                    slot_datetime = timezone.make_aware(datetime.combine(preferred_date, slot_time))
                    buffer_time = now + timedelta(hours=1)
                    
                    if slot_datetime <= buffer_time:
                        raise ValidationError({
                            'preferred_time': 'Выберите время минимум через час от текущего времени'
                        })
                except ValueError:
                    raise ValidationError({
                        'preferred_time': 'Некорректный формат времени'
                    })
            
            # ПРОВЕРКА КОНФЛИКТОВ ВРЕМЕНИ
            try:
                from .validators import ConflictValidator
                
                # Создаем datetime объекты для проверки
                start_datetime = timezone.make_aware(
                    datetime.combine(preferred_date, datetime.strptime(preferred_time, '%H:%M').time())
                )
                end_datetime = start_datetime + timedelta(minutes=service.duration)
                
                # 1. Проверяем конфликты специалиста (другой пациент на это же время)
                has_conflicts, conflict_descriptions = ConflictValidator.check_appointment_conflicts(
                    specialist, start_datetime, end_datetime
                )
                
                if has_conflicts:
                    # Получаем доступные слоты
                    from .validators import DateTimeValidator
                    dt_validator = DateTimeValidator()
                    available_slots = dt_validator.get_available_time_slots(preferred_date, service.duration)
                    
                    if available_slots:
                        slots_str = ", ".join([slot['time'] for slot in available_slots[:5]])
                        error_msg = f"Это время уже занято. Доступные слоты: {slots_str}"
                    else:
                        error_msg = "Это время уже занято. Выберите другой день."
                    
                    raise ValidationError({
                        'preferred_time': error_msg
                    })
                
                # 2. Проверяем двойное бронирование пациента (сам пациент уже записан на это время)
                phone = cleaned_data.get('phone')
                if phone:
                    has_double_booking, double_booking_error = ConflictValidator.check_patient_double_booking(
                        phone, start_datetime, end_datetime
                    )
                    
                    if has_double_booking:
                        raise ValidationError({
                            'preferred_time': double_booking_error
                        })
                    
            except ValidationError:
                raise  # Пробрасываем ValidationError дальше
            except Exception as e:
                # Если ошибка в валидации, не блокируем создание записи
                print(f"Ошибка проверки конфликтов: {e}")
        
        return cleaned_data

    def save(self, commit=True):
        appointment = super().save(commit=False)
        
        # Устанавливаем время начала и окончания
        preferred_date = self.cleaned_data['preferred_date']
        preferred_time = self.cleaned_data['preferred_time']
        
        # Создаем timezone-aware datetime объект
        start_datetime = datetime.combine(preferred_date, datetime.strptime(preferred_time, '%H:%M').time())
        start_datetime = timezone.make_aware(start_datetime)
        appointment.start_time = start_datetime
        
        # Время окончания = время начала + длительность услуги
        duration = timedelta(minutes=appointment.service.duration)
        appointment.end_time = start_datetime + duration
        
        if commit:
            appointment.save()
        return appointment
