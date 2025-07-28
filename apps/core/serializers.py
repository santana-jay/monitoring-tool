from rest_framework import serializers
from .models import MonitoringSystem, Metric, Incident, PatternAnomaly


class MonitoringSystemSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonitoringSystem
        fields = '__all__'


class MetricSerializer(serializers.ModelSerializer):
    system_name = serializers.CharField(source='system.name', read_only=True)
    
    class Meta:
        model = Metric
        fields = ['id', 'time', 'system', 'system_name', 'metric_name', 
                 'metric_value', 'tags', 'unit']


class IncidentSerializer(serializers.ModelSerializer):
    system_name = serializers.CharField(source='system.name', read_only=True)

    class Meta:
        model = Incident
        fields = '__all__'


class PatternAnomalySerializer(serializers.ModelSerializer):
    system_name = serializers.CharField(source='system.name', read_only=True)

    class Meta:
        model = PatternAnomaly
        fields = '__all__'