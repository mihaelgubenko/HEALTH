from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
import logging

logger = logging.getLogger(__name__)


class EmailService:
    """Сервис для отправки email уведомлений"""
    
    @staticmethod
    def send_appointment_confirmation(appointment):
        """Отправка подтверждения записи пациенту"""
        if not appointment.patient.email:
            logger.info(f"Email не указан для пациента {appointment.patient.name}")
            return False
            
        try:
            subject = f"Подтверждение записи - Центр 'Новая Жизнь'"
            
            # HTML версия письма
            html_message = render_to_string('emails/appointment_confirmation.html', {
                'appointment': appointment,
                'patient': appointment.patient,
                'service': appointment.service,
                'specialist': appointment.specialist,
                'center_name': settings.CENTER_NAME,
                'center_phone': settings.PHONE_MAIN,
                'center_address': settings.CENTER_ADDRESS,
            })
            
            # Текстовая версия (fallback)
            plain_message = strip_tags(html_message)
            
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[appointment.patient.email],
                html_message=html_message,
                fail_silently=False,
            )
            
            logger.info(f"Email отправлен пациенту {appointment.patient.email}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка отправки email: {e}")
            return False
    
    @staticmethod
    def send_appointment_reminder(appointment):
        """Отправка напоминания о записи"""
        if not appointment.patient.email:
            return False
            
        try:
            subject = f"Напоминание о записи - Центр 'Новая Жизнь'"
            
            html_message = render_to_string('emails/appointment_reminder.html', {
                'appointment': appointment,
                'patient': appointment.patient,
                'service': appointment.service,
                'specialist': appointment.specialist,
                'center_name': settings.CENTER_NAME,
                'center_phone': settings.PHONE_MAIN,
            })
            
            plain_message = strip_tags(html_message)
            
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[appointment.patient.email],
                html_message=html_message,
                fail_silently=False,
            )
            
            logger.info(f"Напоминание отправлено пациенту {appointment.patient.email}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка отправки напоминания: {e}")
            return False
    
    @staticmethod
    def send_admin_notification(appointment):
        """Отправка уведомления администратору о новой записи"""
        try:
            subject = f"Новая запись на сайте - {appointment.patient.name}"
            
            html_message = render_to_string('emails/admin_notification.html', {
                'appointment': appointment,
                'patient': appointment.patient,
                'service': appointment.service,
                'specialist': appointment.specialist,
            })
            
            plain_message = strip_tags(html_message)
            
            # Отправляем администраторам
            admin_emails = [email for name, email in settings.ADMINS]
            if admin_emails:
                send_mail(
                    subject=subject,
                    message=plain_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=admin_emails,
                    html_message=html_message,
                    fail_silently=False,
                )
                
                logger.info(f"Уведомление отправлено администраторам: {admin_emails}")
                return True
            
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления админу: {e}")
            return False
