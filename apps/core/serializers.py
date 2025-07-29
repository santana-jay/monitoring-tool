from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Category, Ticket, TicketComment, Solution, 
    TicketSolution, TicketPattern, TicketAnalytics
)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']


class CategorySerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    ticket_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'parent', 'parent_name', 'color', 'ticket_count', 'created_at']
    
    def get_ticket_count(self, obj):
        return obj.ticket_set.count()


class TicketCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    author_username = serializers.CharField(source='author.username', read_only=True)
    
    class Meta:
        model = TicketComment
        fields = ['id', 'content', 'is_internal', 'author', 'author_name', 'author_username', 'created_at']


class SolutionListSerializer(serializers.ModelSerializer):
    """Simplified solution serializer for lists"""
    success_rate = serializers.ReadOnlyField()
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = Solution
        fields = [
            'id', 'title', 'description', 'category_name', 
            'success_rate', 'times_suggested', 'times_successful'
        ]


class SolutionDetailSerializer(serializers.ModelSerializer):
    """Detailed solution serializer"""
    success_rate = serializers.ReadOnlyField()
    category_name = serializers.CharField(source='category.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = Solution
        fields = '__all__'


class TicketSolutionSerializer(serializers.ModelSerializer):
    solution_title = serializers.CharField(source='solution.title', read_only=True)
    applied_by_name = serializers.CharField(source='applied_by.get_full_name', read_only=True)
    
    class Meta:
        model = TicketSolution
        fields = ['id', 'solution', 'solution_title', 'was_successful', 'notes', 'applied_by', 'applied_by_name', 'applied_at']


class TicketListSerializer(serializers.ModelSerializer):
    """Simplified ticket serializer for lists"""
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_color = serializers.CharField(source='category.color', read_only=True)
    comments_count = serializers.SerializerMethodField()
    resolution_time_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Ticket
        fields = [
            'id', 'title', 'status', 'priority', 'category_name', 'category_color',
            'created_by', 'created_by_name', 'assigned_to', 'assigned_to_name',
            'created_at', 'updated_at', 'resolved_at', 'comments_count', 'resolution_time_display'
        ]
    
    def get_comments_count(self, obj):
        return obj.comments.count()
    
    def get_resolution_time_display(self, obj):
        if obj.resolution_time_minutes:
            hours = obj.resolution_time_minutes // 60
            minutes = obj.resolution_time_minutes % 60
            if hours > 0:
                return f"{hours}h {minutes}m"
            return f"{minutes}m"
        return None


class TicketDetailSerializer(serializers.ModelSerializer):
    """Detailed ticket serializer"""
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_color = serializers.CharField(source='category.color', read_only=True)
    comments = TicketCommentSerializer(many=True, read_only=True)
    tried_solutions = TicketSolutionSerializer(many=True, read_only=True)
    resolution_time_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Ticket
        fields = '__all__'
    
    def get_resolution_time_display(self, obj):
        if obj.resolution_time_minutes:
            hours = obj.resolution_time_minutes // 60
            minutes = obj.resolution_time_minutes % 60
            if hours > 0:
                return f"{hours}h {minutes}m"
            return f"{minutes}m"
        return None


class TicketCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating tickets"""
    class Meta:
        model = Ticket
        fields = ['title', 'description', 'category', 'priority', 'system_info']
    
    def create(self, validated_data):
        # Set the created_by field to the current user
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class TicketPatternSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    suggested_solutions = SolutionListSerializer(many=True, read_only=True)
    helpfulness_rate = serializers.ReadOnlyField()
    
    class Meta:
        model = TicketPattern
        fields = '__all__'


class TicketAnalyticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketAnalytics
        fields = '__all__'


class DashboardStatsSerializer(serializers.Serializer):
    """Serializer for dashboard statistics"""
    total_tickets = serializers.IntegerField()
    open_tickets = serializers.IntegerField()
    in_progress_tickets = serializers.IntegerField()
    resolved_today = serializers.IntegerField()
    my_tickets = serializers.IntegerField()
    avg_resolution_time = serializers.CharField()
    most_common_category = serializers.CharField()
    recent_tickets = TicketListSerializer(many=True)


class SolutionSuggestionSerializer(serializers.Serializer):
    """Serializer for solution suggestions"""
    solution = SolutionListSerializer()
    confidence_score = serializers.FloatField()
    match_reason = serializers.CharField()
    suggested_by = serializers.CharField()  # 'keyword_match', 'pattern_match', 'category_match'