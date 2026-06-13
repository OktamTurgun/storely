import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('storely')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'check-low-stock-daily': {
        'task': 'apps.notifications.tasks.check_low_stock_all_stores',
        'schedule': crontab(hour=8, minute=0),
    },
    'send-daily-report': {
        'task': 'apps.notifications.tasks.send_daily_report_all_stores',
        'schedule': crontab(hour=20, minute=0),
    },
}