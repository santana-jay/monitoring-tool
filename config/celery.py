from celery import Celery
from celery.schedules import crontab
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('monitoring')
app.config_from_object('django.conf:settings', namespace='Celery')
app.autodiscover_tasks()

# Periodic task schedule
app.conf.beat_schedule = {
    'collect-system-metrics': {
        'task': 'apps.collectors.system_collector.collect_system_metrics_task',
        'schedule': crontab(minute='*/2'), # Every 2 minutes
    },
}

app.conf.timezone = 'UTC'

@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")