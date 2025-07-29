from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Category(models.Model):
    """Ticket categories for organization"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE)
    color = models.CharField(max_length=7, default='#3498db')  # Hex color
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']


class Ticket(models.Model):
    PRIORITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('URGENT', 'Urgent'),
    ]

    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('IN_PROGRESS', 'In Progress'),
        ('WAITING_USER', 'Waiting for User'),
        ('RESOLVED', 'Resolved'),
        ('CLOSED', 'Closed'),
    ]

    # Basic ticket info
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    
    # People involved
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_tickets')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tickets')
    
    # Status and priority
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='MEDIUM')
    
    # System information (for context)
    system_info = models.JSONField(default=dict, blank=True, help_text="OS, software versions, etc.")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    
    # Resolution info
    resolution = models.TextField(blank=True)
    resolution_time_minutes = models.IntegerField(null=True, blank=True)
    
    def save(self, *args, **kwargs):
        # Calculate resolution time when ticket is resolved
        if self.status == 'RESOLVED' and not self.resolved_at:
            self.resolved_at = timezone.now()
        
        # Calculate resolution time if both dates are available
        if self.resolved_at and self.created_at and not self.resolution_time_minutes:
            # Ensure both datetimes are timezone-aware for calculation
            resolved_at = self.resolved_at
            created_at = self.created_at
            
            # Make sure both are timezone-aware
            if timezone.is_naive(resolved_at):
                resolved_at = timezone.make_aware(resolved_at)
            if timezone.is_naive(created_at):
                created_at = timezone.make_aware(created_at)
                
            delta = resolved_at - created_at
            self.resolution_time_minutes = int(delta.total_seconds() / 60)
        
        # Set closed time when ticket is closed
        if self.status == 'CLOSED' and not self.closed_at:
            self.closed_at = timezone.now()
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"#{self.id} - {self.title}"

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['category', 'created_at']),
            models.Index(fields=['assigned_to', 'status']),
        ]


class TicketComment(models.Model):
    """Comments/updates on tickets"""
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    is_internal = models.BooleanField(default=False, help_text="Internal notes not visible to ticket creator")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment on {self.ticket.title} by {self.author.username}"

    class Meta:
        ordering = ['created_at']


class Solution(models.Model):
    """Knowledge base of solutions"""
    title = models.CharField(max_length=200)
    description = models.TextField()
    steps = models.TextField(help_text="Step-by-step solution")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Keywords for matching
    keywords = models.TextField(help_text="Comma-separated keywords for matching", blank=True)
    
    # Effectiveness tracking
    times_suggested = models.IntegerField(default=0)
    times_successful = models.IntegerField(default=0)
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    @property
    def success_rate(self):
        if self.times_suggested == 0:
            return 0.0
        return float((self.times_successful / self.times_suggested) * 100)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-times_successful', '-created_at']


class TicketSolution(models.Model):
    """Track which solutions were tried for tickets"""
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='tried_solutions')
    solution = models.ForeignKey(Solution, on_delete=models.CASCADE, related_name='ticket_applications')
    
    was_successful = models.BooleanField(null=True, blank=True)
    notes = models.TextField(blank=True)
    applied_by = models.ForeignKey(User, on_delete=models.CASCADE)
    applied_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Update solution statistics
        if self.pk is None:  # New instance
            self.solution.times_suggested += 1
            if self.was_successful:
                self.solution.times_successful += 1
            self.solution.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.solution.title} for {self.ticket.title}"

    class Meta:
        unique_together = ['ticket', 'solution']


class TicketPattern(models.Model):
    """AI-detected patterns in tickets"""
    PATTERN_TYPES = [
        ('KEYWORD', 'Keyword Pattern'),
        ('CATEGORY', 'Category Pattern'),
        ('TIME', 'Time-based Pattern'),
        ('USER', 'User Pattern'),
        ('SYMPTOM', 'Symptom Pattern'),
    ]

    pattern_type = models.CharField(max_length=20, choices=PATTERN_TYPES)
    pattern_data = models.JSONField(help_text="Pattern details and parameters")
    
    # Pattern matching
    matching_keywords = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Suggested solutions
    suggested_solutions = models.ManyToManyField(Solution, blank=True)
    
    # Effectiveness
    confidence_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    times_matched = models.IntegerField(default=0)
    times_helpful = models.IntegerField(default=0)
    
    # Metadata
    discovered_at = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    @property
    def helpfulness_rate(self):
        if self.times_matched == 0:
            return 0.0
        return float((self.times_helpful / self.times_matched) * 100)

    def __str__(self):
        return f"{self.pattern_type} Pattern (Confidence: {self.confidence_score}%)"

    class Meta:
        ordering = ['-confidence_score', '-times_helpful']


class TicketAnalytics(models.Model):
    """Store analytics data for reporting"""
    date = models.DateField()
    
    # Daily metrics
    tickets_created = models.IntegerField(default=0)
    tickets_resolved = models.IntegerField(default=0)
    tickets_closed = models.IntegerField(default=0)
    
    # Category breakdown
    category_breakdown = models.JSONField(default=dict)
    
    # Performance metrics
    avg_resolution_time = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    avg_first_response_time = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Analytics for {self.date}"

    class Meta:
        unique_together = ['date']
        ordering = ['-date']