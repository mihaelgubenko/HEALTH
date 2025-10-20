from django.contrib import admin
from django.utils.html import format_html
from django.urls import path
from django.shortcuts import redirect
from .models import Patient, Service, Specialist, Appointment, DialogLog, FAQ, ContactMessage
from .admin_dashboard import dashboard


class PatientAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'country', 'city', 'created_at']
    list_filter = ['country', 'created_at']
    search_fields = ['name', 'phone', 'email']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']


class ServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'currency', 'duration', 'catalog', 'is_active']
    list_filter = ['catalog', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at']
    ordering = ['catalog', 'name']


class SpecialistAdmin(admin.ModelAdmin):
    list_display = ['name', 'specialty', 'is_active', 'created_at']
    list_filter = ['specialty', 'is_active', 'created_at']
    search_fields = ['name', 'specialty']
    readonly_fields = ['created_at']
    ordering = ['name']


class AppointmentAdmin(admin.ModelAdmin):
    list_display = ['patient', 'specialist', 'service', 'start_time', 'status', 'channel', 'created_at']
    list_filter = ['status', 'channel', 'specialist', 'start_time', 'created_at']
    search_fields = ['patient__name', 'patient__phone', 'specialist__name']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['start_time']
    actions = ['confirm_appointments', 'cancel_appointments', 'complete_appointments']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('patient', 'specialist', 'service')
    
    def confirm_appointments(self, request, queryset):
        """Подтвердить записи"""
        updated = queryset.update(status='confirmed')
        self.message_user(request, f'Подтверждено записей: {updated}')
    confirm_appointments.short_description = "✅ Подтвердить выбранные записи"
    
    def cancel_appointments(self, request, queryset):
        """Отменить записи"""
        updated = queryset.update(status='cancelled')
        self.message_user(request, f'Отменено записей: {updated}')
    cancel_appointments.short_description = "❌ Отменить выбранные записи"
    
    def complete_appointments(self, request, queryset):
        """Завершить записи"""
        updated = queryset.update(status='completed')
        self.message_user(request, f'Завершено записей: {updated}')
    complete_appointments.short_description = "✅ Завершить выбранные записи"


# УДАЛЕНО: ReminderAdmin (напоминания не используются в минимальной конфигурации)


class DialogLogAdmin(admin.ModelAdmin):
    list_display = ['channel', 'intent', 'language', 'duration', 'created_at']
    list_filter = ['channel', 'intent', 'language', 'created_at']
    search_fields = ['transcript', 'patient__name']
    readonly_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('patient')


class FAQAdmin(admin.ModelAdmin):
    list_display = ['question', 'category', 'language', 'is_active', 'order']
    list_filter = ['category', 'language', 'is_active']
    search_fields = ['question', 'answer']
    readonly_fields = ['created_at']
    ordering = ['category', 'order', 'question']


class ContactMessageAdmin(admin.ModelAdmin):
    """Админка для сообщений контактов"""
    list_display = ['name', 'phone', 'email', 'created_at', 'is_read', 'message_preview']
    list_filter = ['is_read', 'created_at']
    search_fields = ['name', 'phone', 'email', 'message']
    readonly_fields = ['created_at']
    ordering = ['-created_at']
    
    def message_preview(self, obj):
        """Превью сообщения (первые 50 символов)"""
        if len(obj.message) > 50:
            return obj.message[:50] + "..."
        return obj.message
    message_preview.short_description = "Превью сообщения"
    
    def get_queryset(self, request):
        return super().get_queryset(request)
    
    # Добавляем счетчик непрочитанных сообщений в заголовок
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        unread_count = ContactMessage.objects.filter(is_read=False).count()
        extra_context['unread_messages_count'] = unread_count
        return super().changelist_view(request, extra_context)


# Кастомизация админки
class CustomAdminSite(admin.AdminSite):
    site_header = "Центр здоровья 'Новая Жизнь'"
    site_title = "Админ панель"
    index_title = "Управление медицинским центром"
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('dashboard/', dashboard.dashboard_view, name='admin_dashboard'),
        ]
        return custom_urls + urls
    
    def index(self, request, extra_context=None):
        # Показываем стандартную главную страницу админки
        return super().index(request, extra_context)
    
    def get_app_list(self, request):
        """Возвращаем стандартный список приложений"""
        return super().get_app_list(request)


# Создаем кастомный сайт админки
admin_site = CustomAdminSite(name='admin')

# Регистрируем модели в кастомном сайте
admin_site.register(Patient, PatientAdmin)
admin_site.register(Service, ServiceAdmin) 
admin_site.register(Specialist, SpecialistAdmin)
admin_site.register(Appointment, AppointmentAdmin)
admin_site.register(DialogLog, DialogLogAdmin)
admin_site.register(FAQ, FAQAdmin)
admin_site.register(ContactMessage, ContactMessageAdmin)

# Также регистрируем в стандартном сайте для совместимости
admin.site.site_header = "Центр здоровья 'Новая Жизнь'"
admin.site.site_title = "Админ панель"
admin.site.index_title = "Управление медицинским центром"