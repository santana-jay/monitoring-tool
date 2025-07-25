from django.db import models

# Create your models here.

class MonitoringSystem(models.Model):
    SYSTEM_TYPES = [
        ('SAP', 'SAP Sysstem'),
        ('WMS', 'Warehouse Management System'),
        ('WINDOWS', 'Windows Server'),
        ('LINUX', 'Linux Server'),
        ('NETWORK', 'Network Device'),
    ]

    name = models.CharField(max_length=100)
    system_type = models.CharField(max_length=50, choices=SYSTEM_TYPES)
    host = models.CharField(max_length=255)
    port = models.IntegerField(null=True, blank=True)
    connection_params = models.JSONField(default=dict)
    status = models.CharField(max_length=20, default='active')
    last_check = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.system_type})"
    
    class Meta:
        verbose_name = 'Monitoring System'
        verbose_name_plural = 'Monitoring Systems'


class Metric(models.Model):
    time = models.DateTimeField()
    system = models.ForeignKey(MonitoringSystem, on_delete=models.CASCADE)
    metric_name = models.CharField(max_length=100)
    metric_value = models.DecimalField(max_digits=15, decimal_places=4)
    tags = models.JSONField(default=dict)
    unit = models.CharField(max_length=20, blank=True)

    class Meta:
        db_table = 'metrics'
        indexes = [
            models.Index(fields=['time', 'system', 'metric_name']),
            models.Index(fields=['metric_name', 'time']),
        ]
        ordering = ['-time']

    def __str__(self):
        return f"{self.system.name} - {self.metric_name}: {self.metric_value}"


class Incident(models.Model):
    SEVERITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]

    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('INVESTIGATING', 'Investigating'),
        ('RESOLVED', 'Resolved'),
    ]

    system = models.ForeignKey(MonitoringSystem, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    status = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='OPEN')
    root_cause = models.TextField(blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.severity}"
    
    class Meta:
        ordering = ['-created_at']

    
class PatternAnomaly(models.Model):
    system = models.ForeignKey(MonitoringSystem, on_delete=models.CASCADE)
    anomaly_type = models.CharField(max_length=50)
    confidence_score = models.DecimalField(max_digits=3, decimal_places=2)
    baseline_value = models.DecimalField(max_digits=15, decimal_places=4, null=True)
    actual_value = models.DecimalField(max_digits=15, decimal_places=4)
    deviation_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    detected_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.system.name} - {self.anomaly_type} ({self.confidence_score})"

    class Meta:
        ordering = ['-detected_at']
        verbose_name = "Pattern Anomaly"
        verbose_name_plural = "Pattern Anomalies"
