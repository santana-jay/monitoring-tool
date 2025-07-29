from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    Category, Ticket, TicketComment, Solution, 
    TicketSolution, TicketPattern, TicketAnalytics
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'ticket_count', 'color_display']
    list_filter = ['parent']
    search_fields = ['name', 'description']
    prepopulated_fields = {'name': ()}
    
    def ticket_count(self, obj):
        return obj.ticket_set.count()
    ticket_count.short_description = 'Tickets'
    
    def color_display(self, obj):
        return format_html(
            '<div style="width: 30px; height: 20px; background-color: {}; border: 1px solid #ccc;"></div>',
            obj.color
        )
    color_display.short_description = 'Color'


class TicketCommentInline(admin.TabularInline):
    model = TicketComment
    extra = 0
    readonly_fields = ['created_at']
    fields = ['author', 'content', 'is_internal', 'created_at']


class TicketSolutionInline(admin.TabularInline):
    model = TicketSolution
    extra = 0
    readonly_fields = ['applied_at']
    fields = ['solution', 'was_successful', 'notes', 'applied_by', 'applied_at']


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'title', 'status', 'priority', 'category', 
        'assigned_to', 'created_by', 'created_at', 'resolution_time_display'
    ]
    list_filter = [
        'status', 'priority', 'category', 'created_at', 
        'assigned_to', 'resolved_at'
    ]
    search_fields = ['title', 'description', 'resolution']
    readonly_fields = [
        'created_at', 'updated_at', 'resolved_at', 'closed_at', 
        'resolution_time_minutes', 'resolution_time_display'
    ]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'category', 'priority')
        }),
        ('Assignment', {
            'fields': ('created_by', 'assigned_to', 'status')
        }),
        ('System Information', {
            'fields': ('system_info',),
            'classes': ('collapse',)
        }),
        ('Resolution', {
            'fields': ('resolution', 'resolution_time_display'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': (
                'created_at', 'updated_at', 'resolved_at', 
                'closed_at', 'resolution_time_minutes'
            ),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [TicketCommentInline, TicketSolutionInline]
    
    def resolution_time_display(self, obj):
        try:
            if obj.resolution_time_minutes:
                hours = obj.resolution_time_minutes // 60
                minutes = obj.resolution_time_minutes % 60
                if hours > 0:
                    return f"{hours}h {minutes}m"
                return f"{minutes}m"
            return "Not resolved"
        except (TypeError, AttributeError):
            return "N/A"
    resolution_time_display.short_description = 'Resolution Time'
    
    actions = ['mark_resolved', 'mark_closed', 'assign_to_me']
    
    def mark_resolved(self, request, queryset):
        updated = queryset.update(status='RESOLVED')
        self.message_user(request, f'{updated} tickets marked as resolved.')
    mark_resolved.short_description = 'Mark selected tickets as resolved'
    
    def mark_closed(self, request, queryset):
        updated = queryset.update(status='CLOSED')
        self.message_user(request, f'{updated} tickets marked as closed.')
    mark_closed.short_description = 'Mark selected tickets as closed'
    
    def assign_to_me(self, request, queryset):
        updated = queryset.update(assigned_to=request.user)
        self.message_user(request, f'{updated} tickets assigned to you.')
    assign_to_me.short_description = 'Assign selected tickets to me'


@admin.register(TicketComment)
class TicketCommentAdmin(admin.ModelAdmin):
    list_display = ['ticket', 'author', 'content_preview', 'is_internal', 'created_at']
    list_filter = ['is_internal', 'created_at', 'author']
    search_fields = ['content', 'ticket__title']
    readonly_fields = ['created_at']
    
    def content_preview(self, obj):
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
    content_preview.short_description = 'Content'


@admin.register(Solution)
class SolutionAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'category', 'success_rate_display', 
        'times_suggested', 'times_successful', 'is_active'
    ]
    list_filter = ['category', 'is_active', 'created_at']
    search_fields = ['title', 'description', 'keywords']
    readonly_fields = ['times_suggested', 'times_successful', 'success_rate_display', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Solution Details', {
            'fields': ('title', 'description', 'steps', 'category', 'keywords')
        }),
        ('Effectiveness', {
            'fields': (
                'times_suggested', 'times_successful', 'success_rate_display'
            ),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'is_active', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def success_rate_display(self, obj):
        """Display success rate with proper SafeString handling"""
        try:
            if obj.times_suggested == 0:
                return format_html('<span style="color: gray;">0.0%</span>')
            
            rate = (obj.times_successful / obj.times_suggested) * 100
            rate = min(rate, 100.0)  # Cap at 100%
            
            # Format the percentage first as a regular string
            rate_str = f"{rate:.1f}%"
            
            # Color coding
            if rate >= 70:
                color = 'green'
            elif rate >= 40:
                color = 'orange'  
            else:
                color = 'red'
            
            # Use format_html with pre-formatted string
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}</span>',
                color, rate_str
            )
        except Exception as e:
            # Show the actual error for debugging
            return format_html('<span style="color: red;">Error: {}</span>', str(e))
    success_rate_display.short_description = 'Success Rate'


@admin.register(TicketSolution)
class TicketSolutionAdmin(admin.ModelAdmin):
    list_display = ['ticket', 'solution', 'was_successful', 'applied_by', 'applied_at']
    list_filter = ['was_successful', 'applied_at', 'applied_by']
    search_fields = ['ticket__title', 'solution__title', 'notes']
    readonly_fields = ['applied_at']


@admin.register(TicketPattern)
class TicketPatternAdmin(admin.ModelAdmin):
    list_display = [
        'pattern_type', 'confidence_score', 'helpfulness_display',
        'times_matched', 'is_active', 'last_seen'
    ]
    list_filter = ['pattern_type', 'is_active', 'category', 'discovered_at']
    search_fields = ['matching_keywords', 'pattern_data']
    readonly_fields = ['discovered_at', 'last_seen', 'times_matched', 'times_helpful', 'helpfulness_display']
    filter_horizontal = ['suggested_solutions']
    
    def helpfulness_display(self, obj):
        """Display helpfulness rate with proper SafeString handling"""
        try:
            if obj.times_matched == 0:
                return format_html('<span style="color: gray;">0.0%</span>')
            
            rate = (obj.times_helpful / obj.times_matched) * 100
            rate = min(rate, 100.0)  # Cap at 100%
            
            # Format the percentage first as a regular string
            rate_str = f"{rate:.1f}%"
            
            # Color coding
            if rate >= 70:
                color = 'green'
            elif rate >= 40:
                color = 'orange'  
            else:
                color = 'red'
            
            # Use format_html with pre-formatted string
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}</span>',
                color, rate_str
            )
        except Exception as e:
            return format_html('<span style="color: red;">Error: {}</span>', str(e))
    helpfulness_display.short_description = 'Helpfulness Rate'


@admin.register(TicketAnalytics)
class TicketAnalyticsAdmin(admin.ModelAdmin):
    list_display = [
        'date', 'tickets_created', 'tickets_resolved', 
        'tickets_closed', 'avg_resolution_time'
    ]
    list_filter = ['date']
    readonly_fields = ['created_at']
    date_hierarchy = 'date'
    
    def has_add_permission(self, request):
        # Analytics should be generated automatically
        return False