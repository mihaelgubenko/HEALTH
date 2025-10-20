from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Appointment, Service, Specialist
from datetime import datetime, timedelta


class AppointmentForm(forms.ModelForm):
    """Форма записи на прием"""
    
    name = forms.CharField(
        max_length=100,
        label='Ваше имя',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите ваше имя'
        })
    )
    
    phone = forms.CharField(
        max_length=20,
        label='Телефон',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+972545270015'
        })
    )
    
    email = forms.EmailField(
        required=False,
        label='Email (необязательно)',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'your@email.com'
        })
    )
    
    preferred_date = forms.DateField(
        label='Предпочитаемая дата',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'min': datetime.now().strftime('%Y-%m-%d')
        })
    )
    
    preferred_time = forms.ChoiceField(
        label='Предпочитаемое время',
        choices=[],
        widget=forms.Select(attrs={
            'class': 'form-control'
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
            'service': forms.Select(attrs={'class': 'form-control'}),
            'specialist': forms.Select(attrs={'class': 'form-control'}),
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
        time_choices = [
            ('09:00', '09:00'),
            ('10:00', '10:00'),
            ('11:00', '11:00'),
            ('12:00', '12:00'),
            ('15:00', '15:00'),
            ('16:00', '16:00'),
            ('17:00', '17:00'),
            ('18:00', '18:00'),
            ('19:00', '19:00'),
        ]
        self.fields['preferred_time'].choices = time_choices

    def clean_phone(self):
        phone = self.cleaned_data['phone']
        # Простая валидация телефона
        if not phone.startswith('+'):
            phone = '+' + phone
        return phone

    def clean_preferred_date(self):
        date = self.cleaned_data['preferred_date']
        if date < datetime.now().date():
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
