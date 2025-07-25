import psutil
from datetime import datetime
from celery import shared_task
from apps.core.models import MonitoringSystem, Metric
import logging
from loguru import logger

# Configure loguru
logger.add('logs/monitoring.log', rotation='1 day', retention='30 days')

def collect_local_system_metrics():
    """ Collect basic system metrics from the local machine """
    try:
        # Get or create a local system entry
        system, created = MonitoringSystem.objects.get_or_create(
            name = 'Codespaces System',
            defaults={
                'system_type': 'LINUX',
                'host': 'localhost',
                'status': 'active'
            }
        )

        if created:
            logger.info(f"Created new system: {system.name}")

        # Collect basic metrics
        metrics_data = []

        # CPU Usage
        cpu_percent = psutil.cpu_percent(interval=1)
        metrics_data.append({
            'metric_name': 'cpu_utilization',
            'metric_value': cpu_percent,
            'unit': 'percent',
            'tags': {'component': 'cpu'}
        })

        # Memory Usage
        memory = psutil.virtual_memory()
        metrics_data.append({
            'metric_name': 'memory_utilization',
            'metric_value': memory.percent,
            'unit': 'percent',
            'tags': {'component': 'memory'}
        })

        # Disk Usage
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        metrics_data.append({
            'metric_name': 'disk_utilization',
            'metric_value': round(disk_percent, 2),
            'unit': 'percent',
            'tags': {'component': 'disk', 'mount': '/'}
        })

        # Network I/O
        net_io = psutil.net_io_counters()
        metrics_data.extend([
            {
                'metric_name': 'network_bytes_sent',
                'metric_value': net_io.bytes_sent,
                'unit': 'bytes',
                'tags': {'component': 'network', 'direction': 'in'}
            },
            {
                'metric_name': 'network_bytes_received',
                'metric_value': net_io.bytes_recv,
                'unit': 'bytes',
                'tags': {'component': 'network', 'direction': 'in'}
            }
        ])

        # Save all metrics to database
        now = datetime.now()
        for metric_data in metrics_data:
            Metric.objects.create(
                time=now,
                system=system,
                **metric_data
            )

        # Update last check time
        system.last_check = now
        system.save()

        logger.info(f"Collected {len(metrics_data)} metrics for {system.name}")
        return {
            'success': True,
            'metric_count': len(metrics_data),
            'system': system.name
        }
    
    except Exception as e:
        logger.error(f"Failed to collect system metrics: {e}")
        return {
            'success': False,
            'error': str(e)
        }
    
@shared_task
def collect_system_metrics_task():
    """Celery task wrapper for system metrics collection"""
    return collect_local_system_metrics()
