"""
URL configuration for smart_secretary project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core.admin import admin_site
from core.admin_validation_api import (
    validate_appointment_data, get_available_slots, check_conflicts,
    validate_patient_data, get_patient_suggestions, AdminValidationAPI
)

urlpatterns = [
    path('admin/', admin_site.urls),  # Кастомная админка с дашбордом
    path('', include('core.urls')),
    
    # API для валидации в админке
    path('admin-api/validate-appointment/', validate_appointment_data, name='admin_validate_appointment'),
    path('admin-api/get-slots/', get_available_slots, name='admin_get_slots'),
    path('admin-api/check-conflicts/', check_conflicts, name='admin_check_conflicts'),
    path('admin-api/validate-patient/', validate_patient_data, name='admin_validate_patient'),
    path('admin-api/patient-suggestions/', get_patient_suggestions, name='admin_patient_suggestions'),
    path('admin-api/<str:validation_type>/', AdminValidationAPI.as_view(), name='admin_validation_api'),
]

# Обслуживание статических файлов в режиме разработки
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
