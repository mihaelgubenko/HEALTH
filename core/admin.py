from django.contrib import admin
from django.utils.html import format_html
from .models import Patient, Service, Specialist, Appointment, DialogLog, FAQ, ContactMessage  # Добавлен ContactMessage


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'country', 'city', 'created_at']
    list_filter = ['country', 'created_at']
    search_fields = ['name', 'phone', 'email']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'currency', 'duration', 'catalog', 'is_active']
    list_filter = ['catalog', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at']
    ordering = ['catalog', 'name']


@admin.register(Specialist)
class SpecialistAdmin(admin.ModelAdmin):
    list_display = ['name', 'specialty', 'is_active', 'created_at']
    list_filter = ['specialty', 'is_active', 'created_at']
    search_fields = ['name', 'specialty']
    readonly_fields = ['created_at']
    ordering = ['name']


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ['patient', 'specialist', 'service', 'start_time', 'status', 'channel', 'created_at']
    list_filter = ['status', 'channel', 'specialist', 'start_time', 'created_at']
    search_fields = ['patient__name', 'patient__phone', 'specialist__name']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['start_time']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('patient', 'specialist', 'service')


# УДАЛЕНО: ReminderAdmin (напоминания не используются в минимальной конфигурации)


@admin.register(DialogLog)
class DialogLogAdmin(admin.ModelAdmin):
    list_display = ['channel', 'intent', 'language', 'duration', 'created_at']
    list_filter = ['channel', 'intent', 'language', 'created_at']
    search_fields = ['transcript', 'patient__name']
    readonly_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('patient')


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ['question', 'category', 'language', 'is_active', 'order']
    list_filter = ['category', 'language', 'is_active']
    search_fields = ['question', 'answer']
    readonly_fields = ['created_at']
    ordering = ['category', 'order', 'question']


@admin.register(ContactMessage)
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


# Настройка заголовков админки
admin.site.site_header = "Умный Секретарь - Центр 'Новая Жизнь'"
admin.site.site_title = "УС Админка"
admin.site.index_title = "Управление системой"