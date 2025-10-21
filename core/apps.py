from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    
    def ready(self):
        """Инициализация при запуске приложения"""
        # Импортируем здесь чтобы избежать циклических зависимостей
        from .scheduler import init_scheduler, reschedule_all_reminders
        
        # Инициализируем планировщик только в основном процессе
        # (не в процессах перезагрузки при --reload)
        import os
        if os.environ.get('RUN_MAIN') != 'true':
            # Это родительский процесс при разработке с --reload
            return
        
        try:
            init_scheduler()
            reschedule_all_reminders()
            logger.info("Scheduler initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing scheduler: {e}", exc_info=True)
