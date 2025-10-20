from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import datetime, timedelta
import json

from .models import Service, Specialist, Patient, Appointment, FAQ, ContactMessage
from .forms import AppointmentForm
from .email_service import EmailService


def home(request):
    """Главная страница"""
    # Получаем популярные услуги (первые 6)
    popular_services = Service.objects.filter(is_active=True, catalog='A')[:6]
    
    context = {
        'popular_services': popular_services,
    }
    return render(request, 'core/home.html', context)


def services(request):
    """Страница всех услуг"""
    services_list = Service.objects.filter(is_active=True, catalog='A').order_by('name')
    
    context = {
        'services': services_list,
    }
    return render(request, 'core/services.html', context)


def service_detail(request, service_id):
    """Детальная страница услуги"""
    service = get_object_or_404(Service, id=service_id, is_active=True)
    
    context = {
        'service': service,
    }
    return render(request, 'core/service_detail.html', context)


def appointment_form(request):
    """Форма записи на прием"""
    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        if form.is_valid():
            # Создаем пациента
            patient, created = Patient.objects.get_or_create(
                phone=form.cleaned_data['phone'],
                defaults={
                    'name': form.cleaned_data['name'],
                    'email': form.cleaned_data.get('email', ''),
                    'country': 'Israel',
                    'city': 'Иерусалим',
                }
            )
            
            # Создаем запись
            appointment = form.save(commit=False)
            appointment.patient = patient
            appointment.channel = 'web'
            appointment.status = 'pending'
            appointment.save()
            
            # Отправляем email уведомления
            try:
                # Уведомление пациенту
                if patient.email:
                    EmailService.send_appointment_confirmation(appointment)
                
                # Уведомление администратору
                EmailService.send_admin_notification(appointment)
                
            except Exception as e:
                # Логируем ошибку, но не прерываем процесс
                print(f"Ошибка отправки email: {e}")
            
            messages.success(request, 'Запись успешно создана! Мы свяжемся с вами для подтверждения.')
            return redirect('core:appointment_success')
    else:
        form = AppointmentForm()
    
    context = {
        'form': form,
    }
    return render(request, 'core/appointment_form.html', context)


def appointment_success(request):
    """Страница успешной записи"""
    return render(request, 'core/appointment_success.html')


def analytics_dashboard(request):
    """Dashboard аналитики работы ИИ-секретаря"""
    from .analytics import SecretaryAnalytics
    
    analytics = SecretaryAnalytics()
    
    context = {
        'daily_stats': analytics.get_daily_stats(),
        'success_rate': analytics.get_success_rate(),
        'popular_services': analytics.get_popular_services(),
        'peak_hours': analytics.get_peak_hours(),
    }
    
    return render(request, 'core/analytics_dashboard.html', context)


def contacts(request):
    """Страница контактов"""
    faq_list = FAQ.objects.filter(is_active=True).order_by('category', 'order')
    
    if request.method == 'POST':
        # Обработка формы контактов
        name = request.POST.get('name', '').strip()
        phone = request.POST.get('phone', '').strip()
        email = request.POST.get('email', '').strip()
        message = request.POST.get('message', '').strip()
        
        # Валидация
        if not name or not phone or not message:
            context = {
                'faq_list': faq_list,
                'error': 'Пожалуйста, заполните все обязательные поля'
            }
            return render(request, 'core/contacts.html', context)
        
        # Сохраняем сообщение в БД
        from .models import ContactMessage
        ContactMessage.objects.create(
            name=name,
            phone=phone,
            email=email if email else None,
            message=message
        )
        
        # Успешная отправка
        context = {
            'faq_list': faq_list,
            'success': 'Сообщение успешно отправлено! Мы свяжемся с вами в ближайшее время.'
        }
        return render(request, 'core/contacts.html', context)
    
    # GET запрос - показать форму
    context = {
        'faq_list': faq_list,
    }
    return render(request, 'core/contacts.html', context)


def get_specialists(request):
    """API для получения специалистов по услуге"""
    service_id = request.GET.get('service_id')
    
    if service_id:
        # Логика выбора специалиста по услуге
        if 'массаж' in Service.objects.get(id=service_id).name.lower():
            specialists = Specialist.objects.filter(name__in=['Авраам', 'Екатерина'])
        elif 'консультация' in Service.objects.get(id=service_id).name.lower():
            specialists = Specialist.objects.filter(name__in=['Екатерина', 'Римма'])
        else:
            specialists = Specialist.objects.filter(is_active=True)
    else:
        specialists = Specialist.objects.filter(is_active=True)
    
    data = [{'id': s.id, 'name': s.name, 'specialty': s.specialty} for s in specialists]
    return JsonResponse(data, safe=False)


def get_available_slots(request):
    """API для получения доступных слотов"""
    specialist_id = request.GET.get('specialist_id')
    date = request.GET.get('date')
    
    if not specialist_id or not date:
        return JsonResponse([], safe=False)
    
    try:
        specialist = Specialist.objects.get(id=specialist_id)
        target_date = datetime.strptime(date, '%Y-%m-%d').date()
        
        # Генерируем слоты на основе рабочих часов специалиста
        slots = []
        day_name = target_date.strftime('%A').lower()
        
        if day_name in specialist.working_hours:
            start_time = specialist.working_hours[day_name]['start']
            end_time = specialist.working_hours[day_name]['end']
            
            # Простая генерация слотов (каждый час)
            start_hour = int(start_time.split(':')[0])
            end_hour = int(end_time.split(':')[0])
            
            for hour in range(start_hour, end_hour):
                slot_time = f"{hour:02d}:00"
                slots.append({
                    'time': slot_time,
                    'display': slot_time
                })
        
        return JsonResponse(slots, safe=False)
        
    except Exception as e:
        return JsonResponse([], safe=False)


def chat(request):
    """Страница чата с ИИ-секретарем"""
    return render(request, 'core/chat.html')
