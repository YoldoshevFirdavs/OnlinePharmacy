import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Enable task events for monitoring
app.conf.update(
    task_send_sent_event=True,
    task_acks_late=True, # Recommended for better reliability
    worker_prefetch_multiplier=1, # Recommended for better reliability
)

app.conf.beat_schedule = {
    'calculate-monthly-payroll': {
        'task': 'users.tasks.calculate_monthly_payroll',
        'schedule': 2592000, # Every month
        'args': (),
    },
}