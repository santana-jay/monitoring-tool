from django.contrib import admin
from .models import MonitoringSystem, Metric, Incident, PatternAnomaly

@admin.register(MonitoringSystem)
class MonitoringSystemAdmin(admin.ModelAdmin):
    list_display = ['name', 'system_type', 'host', 'status', 'last_check']
    list_filter = ['system_type', 'status']
    search_fields = ['name', 'host']
    readonly_fields = ['created_at', 'last_check']

@admin.register(Metric)
class MetricAdmin(admin.ModelAdmin):
    list_display = ['time', 'system', 'metric_name', 'metric_value', 'unit']
    list_filter = ['system', 'metric_name', 'time']
    date_hierarchy = 'time'
    ordering = ['-time']
    readonly_fields = ['time']

@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ['title', 'system', 'severity', 'status', 'created_at']
    list_filter = ['severity', 'status', 'system', 'created_at']
    search_fields = ['title', 'description']
    ordering = ['-created_at']
    readonly_fields = ['created_at']

@admin.register(PatternAnomaly)
class PatternAnomalyAdmin(admin.ModelAdmin):
    list_display = ['system', 'anomaly_type', 'confidence_score', 'detected_at']
    list_filter = ['system', 'anomaly_type', 'detected_at']
    ordering = ['-detected_at']
    readonly_fields = ['detected_at']
