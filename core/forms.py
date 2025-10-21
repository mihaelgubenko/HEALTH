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
            'placeholder': '+972545270015',
            'required': True,
            'type': 'tel',
            'pattern': r'[\+]?[0-9\s\-\(\)]{7,20}'
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
        
        # Заполняем временные слоты (базовые, будут обновляться через JavaScript)
        time_choices = [('', 'Выберите время')]
        
        # Генерируем слоты с учетом текущего времени
        now = timezone.now()
        today = now.date()
        
        # Если форма инициализируется для сегодняшней даты, фильтруем прошедшие слоты
        for hour in range(9, 19):
            for minute in [0, 30]:
                time_str = f'{hour:02d}:{minute:02d}'
                slot_time = datetime.strptime(time_str, '%H:%M').time()
                
                # Для сегодняшней даты пропускаем прошедшие слоты
                if today == now.date():
                    slot_datetime = timezone.make_aware(datetime.combine(today, slot_time))
                    buffer_time = now + timezone.timedelta(hours=1)
                    if slot_datetime <= buffer_time:
                        continue
                
                time_choices.append((time_str, time_str))
        
        self.fields['preferred_time'].choices = time_choices

    def clean_phone(self):
        phone = self.cleaned_data['phone']
        # Простая валидация телефона
        if not phone.startswith('+'):
            phone = '+' + phone
        return phone

    def clean_preferred_date(self):
        date = self.cleaned_data['preferred_date']
        # Используем локальное время пользователя (Israel timezone)
        today = timezone.now().date()
        if date < today:
            raise ValidationError('Дата не может быть в прошлом')
        return date

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
