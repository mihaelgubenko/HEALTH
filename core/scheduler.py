"""
Планировщик задач для автоматической отправки напоминаний
Использует APScheduler для фоновых задач
"""

import logging
from datetime import timedelta
from django.utils import timezone
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from django.conf import settings

logger = logging.getLogger(__name__)

# Глобальный планировщик
scheduler = None


def init_scheduler():
    """Инициализация планировщика при запуске Django"""
    global scheduler
    
    if scheduler is not None:
        logger.info("Scheduler already initialized")
        return scheduler
    
    scheduler = BackgroundScheduler()
    scheduler.start()
    logger.info("Scheduler initialized and started")
    
    # Добавляем регулярную задачу проверки напоминаний каждые 15 минут
    scheduler.add_job(
        check_pending_reminders,
        'interval',
        minutes=15,
        id='check_reminders',
        replace_existing=True
    )
    
    logger.info("Added recurring job: check_pending_reminders every 15 minutes")
    
    return scheduler


def shutdown_scheduler():
    """Остановка планировщика при завершении Django"""
    global scheduler
    
    if scheduler is not None:
        scheduler.shutdown()
        scheduler = None
        logger.info("Scheduler shut down")


def send_reminder_task(reminder_id):
    """
    Задача отправки напоминания
    
    Args:
        reminder_id: ID напоминания
    """
    from .models import Reminder
    from .email_service import EmailService
    
    try:
        reminder = Reminder.objects.select_related(
            'appointment', 
            'appointment__patient', 
            'appointment__specialist', 
            'appointment__service'
        ).get(id=reminder_id)
        
        # Проверяем статус записи
        if reminder.appointment.status not in ['pending', 'confirmed']:
            logger.info(f"Skipping reminder {reminder_id}: appointment status is {reminder.appointment.status}")
            reminder.status = 'cancelled'
            reminder.save()
            return
        
        # Отправляем напоминание
        success = EmailService.send_appointment_reminder(reminder.appointment)
        
        if success:
            reminder.status = 'sent'
            reminder.sent_at = timezone.now()
            logger.info(f"Reminder {reminder_id} sent successfully")
        else:
            reminder.status = 'failed'
            reminder.error_message = 'Email sending failed'
            logger.error(f"Failed to send reminder {reminder_id}")
        
        reminder.save()
        
    except Reminder.DoesNotExist:
        logger.error(f"Reminder {reminder_id} not found")
    except Exception as e:
        logger.error(f"Error sending reminder {reminder_id}: {e}", exc_info=True)
        try:
            reminder = Reminder.objects.get(id=reminder_id)
            reminder.status = 'failed'
            reminder.error_message = str(e)
            reminder.save()
        except Exception:
            pass


def schedule_reminders_for_appointment(appointment):
    """
    Создание напоминаний для записи
    
    Args:
        appointment: Объект записи (Appointment)
        
    Returns:
        Tuple[Reminder, Reminder]: Созданные напоминания (24ч, 2ч)
    """
    from .models import Reminder
    
    if not appointment.patient.email:
        logger.info(f"No email for patient {appointment.patient.name}, skipping reminders")
        return None, None
    
    # Время начала записи
    appointment_time = appointment.start_time
    
    # Напоминание за 24 часа
    reminder_24h_time = appointment_time - timedelta(hours=24)
    reminder_24h = None
    
    if reminder_24h_time > timezone.now():
        reminder_24h = Reminder.objects.create(
            appointment=appointment,
            reminder_type='-24h',
            scheduled_at=reminder_24h_time,
            status='scheduled'
        )
        
        # Планируем отправку в планировщике
        if scheduler:
            try:
                scheduler.add_job(
                    send_reminder_task,
                    DateTrigger(run_date=reminder_24h_time),
                    args=[reminder_24h.id],
                    id=f"reminder_24h_{appointment.id}",
                    replace_existing=True
                )
                logger.info(f"Scheduled 24h reminder for appointment {appointment.id} at {reminder_24h_time}")
            except Exception as e:
                logger.error(f"Error scheduling 24h reminder: {e}")
    
    # Напоминание за 2 часа
    reminder_2h_time = appointment_time - timedelta(hours=2)
    reminder_2h = None
    
    if reminder_2h_time > timezone.now():
        reminder_2h = Reminder.objects.create(
            appointment=appointment,
            reminder_type='-2h',
            scheduled_at=reminder_2h_time,
            status='scheduled'
        )
        
        # Планируем отправку в планировщике
        if scheduler:
            try:
                scheduler.add_job(
                    send_reminder_task,
                    DateTrigger(run_date=reminder_2h_time),
                    args=[reminder_2h.id],
                    id=f"reminder_2h_{appointment.id}",
                    replace_existing=True
                )
                logger.info(f"Scheduled 2h reminder for appointment {appointment.id} at {reminder_2h_time}")
            except Exception as e:
                logger.error(f"Error scheduling 2h reminder: {e}")
    
    return reminder_24h, reminder_2h


def cancel_reminders_for_appointment(appointment):
    """
    Отмена напоминаний для записи
    
    Args:
        appointment: Объект записи (Appointment)
    """
    from .models import Reminder
    
    # Отменяем напоминания в базе
    reminders = Reminder.objects.filter(
        appointment=appointment,
        status='scheduled'
    )
    
    for reminder in reminders:
        reminder.status = 'cancelled'
        reminder.save()
        
        # Удаляем задачу из планировщика
        if scheduler:
            job_id = f"reminder_{reminder.reminder_type}_{appointment.id}"
            try:
                scheduler.remove_job(job_id)
                logger.info(f"Removed scheduled job: {job_id}")
            except Exception as e:
                logger.debug(f"Job {job_id} not found in scheduler: {e}")
    
    logger.info(f"Cancelled {reminders.count()} reminders for appointment {appointment.id}")


def check_pending_reminders():
    """
    Проверка и отправка просроченных напоминаний
    Выполняется каждые 15 минут
    """
    from .models import Reminder
    
    now = timezone.now()
    
    # Находим напоминания, которые должны были быть отправлены
    pending_reminders = Reminder.objects.filter(
        status='scheduled',
        scheduled_at__lte=now
    ).select_related('appointment', 'appointment__patient')
    
    count = pending_reminders.count()
    if count > 0:
        logger.info(f"Found {count} pending reminders to send")
        
        for reminder in pending_reminders:
            send_reminder_task(reminder.id)
    else:
        logger.debug("No pending reminders found")


def reschedule_all_reminders():
    """
    Перепланирование всех активных напоминаний при перезапуске сервера
    """
    from .models import Reminder
    
    now = timezone.now()
    
    # Находим все запланированные напоминания в будущем
    future_reminders = Reminder.objects.filter(
        status='scheduled',
        scheduled_at__gt=now
    ).select_related('appointment')
    
    count = 0
    for reminder in future_reminders:
        if scheduler:
            try:
                scheduler.add_job(
                    send_reminder_task,
                    DateTrigger(run_date=reminder.scheduled_at),
                    args=[reminder.id],
                    id=f"reminder_{reminder.reminder_type}_{reminder.appointment.id}",
                    replace_existing=True
                )
                count += 1
            except Exception as e:
                logger.error(f"Error rescheduling reminder {reminder.id}: {e}")
    
    logger.info(f"Rescheduled {count} reminders")

