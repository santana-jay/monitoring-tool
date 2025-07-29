from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Avg, Q, F
from django.contrib.auth.models import User
from .models import (
    Category, Ticket, TicketComment, Solution, 
    TicketSolution, TicketPattern, TicketAnalytics
)
from .serializers import (
    CategorySerializer, TicketListSerializer, TicketDetailSerializer, 
    TicketCreateSerializer, TicketCommentSerializer, SolutionListSerializer,
    SolutionDetailSerializer, TicketSolutionSerializer, TicketPatternSerializer,
    DashboardStatsSerializer, SolutionSuggestionSerializer, UserSerializer
)
from .utils import SolutionSuggestionEngine, PatternAnalyzer


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]


class TicketViewSet(viewsets.ModelViewSet):
    queryset = Ticket.objects.all()  # Add base queryset
    permission_classes = [permissions.AllowAny]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return TicketListSerializer
        elif self.action == 'create':
            return TicketCreateSerializer
        else:
            return TicketDetailSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            'category', 'created_by', 'assigned_to'
        ).prefetch_related('comments', 'tried_solutions')
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by priority
        priority = self.request.query_params.get('priority')
        if priority:
            queryset = queryset.filter(priority=priority)
        
        # Filter by category
        category_id = self.request.query_params.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        # Filter by assigned user
        assigned_to = self.request.query_params.get('assigned_to')
        if assigned_to == 'me':
            queryset = queryset.filter(assigned_to=self.request.user)
        elif assigned_to:
            queryset = queryset.filter(assigned_to_id=assigned_to)
        
        # Filter by created user
        created_by = self.request.query_params.get('created_by')
        if created_by == 'me':
            queryset = queryset.filter(created_by=self.request.user)
        elif created_by:
            queryset = queryset.filter(created_by_id=created_by)
        
        # Search in title and description
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | 
                Q(description__icontains=search) |
                Q(resolution__icontains=search)
            )
        
        return queryset.order_by('-created_at')
    
    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        """Assign ticket to a user"""
        ticket = self.get_object()
        user_id = request.data.get('user_id')
        
        if user_id:
            try:
                user = User.objects.get(id=user_id)
                ticket.assigned_to = user
                ticket.save()
                
                # Add a comment about the assignment
                TicketComment.objects.create(
                    ticket=ticket,
                    author=request.user,
                    content=f"Ticket assigned to {user.get_full_name() or user.username}",
                    is_internal=True
                )
                
                return Response({'message': 'Ticket assigned successfully'})
            except User.DoesNotExist:
                return Response(
                    {'error': 'User not found'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            # Unassign ticket
            ticket.assigned_to = None
            ticket.save()
            
            TicketComment.objects.create(
                ticket=ticket,
                author=request.user,
                content="Ticket unassigned",
                is_internal=True
            )
            
            return Response({'message': 'Ticket unassigned successfully'})
    
    @action(detail=True, methods=['post'])
    def change_status(self, request, pk=None):
        """Change ticket status"""
        ticket = self.get_object()
        new_status = request.data.get('status')
        
        if new_status not in dict(Ticket.STATUS_CHOICES):
            return Response(
                {'error': 'Invalid status'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        old_status = ticket.status
        ticket.status = new_status
        ticket.save()
        
        # Add a comment about the status change
        TicketComment.objects.create(
            ticket=ticket,
            author=request.user,
            content=f"Status changed from {old_status} to {new_status}",
            is_internal=True
        )
        
        serializer = self.get_serializer(ticket)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_comment(self, request, pk=None):
        """Add a comment to the ticket"""
        ticket = self.get_object()
        
        comment_data = request.data.copy()
        comment_data['ticket'] = ticket.id
        comment_data['author'] = request.user.id
        
        serializer = TicketCommentSerializer(data=comment_data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def suggest_solutions(self, request, pk=None):
        """Get solution suggestions for this ticket"""
        ticket = self.get_object()
        
        # Use the solution suggestion engine
        suggestion_engine = SolutionSuggestionEngine()
        suggestions = suggestion_engine.suggest_solutions(ticket)
        
        serializer = SolutionSuggestionSerializer(suggestions, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def apply_solution(self, request, pk=None):
        """Apply a solution to this ticket"""
        ticket = self.get_object()
        solution_id = request.data.get('solution_id')
        was_successful = request.data.get('was_successful')
        notes = request.data.get('notes', '')
        
        try:
            solution = Solution.objects.get(id=solution_id)
            
            # Record the solution application
            ticket_solution, created = TicketSolution.objects.get_or_create(
                ticket=ticket,
                solution=solution,
                defaults={
                    'applied_by': request.user,
                    'was_successful': was_successful,
                    'notes': notes
                }
            )
            
            if not created:
                # Update existing record
                ticket_solution.was_successful = was_successful
                ticket_solution.notes = notes
                ticket_solution.save()
            
            # Add a comment about the solution
            TicketComment.objects.create(
                ticket=ticket,
                author=request.user,
                content=f"Applied solution: {solution.title}\nResult: {'Successful' if was_successful else 'Not successful'}\nNotes: {notes}",
                is_internal=False
            )
            
            serializer = TicketSolutionSerializer(ticket_solution)
            return Response(serializer.data)
            
        except Solution.DoesNotExist:
            return Response(
                {'error': 'Solution not found'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Get dashboard statistics"""
        user = request.user
        today = timezone.now().date()
        
        # Basic counts
        total_tickets = Ticket.objects.count()
        open_tickets = Ticket.objects.filter(status='OPEN').count()
        in_progress_tickets = Ticket.objects.filter(status='IN_PROGRESS').count()
        resolved_today = Ticket.objects.filter(
            status='RESOLVED', 
            resolved_at__date=today
        ).count()
        my_tickets = Ticket.objects.filter(assigned_to=user).exclude(status='CLOSED').count()
        
        # Average resolution time (in hours)
        avg_resolution = Ticket.objects.filter(
            resolution_time_minutes__isnull=False
        ).aggregate(avg=Avg('resolution_time_minutes'))['avg']
        
        avg_resolution_display = "No data"
        if avg_resolution:
            hours = int(avg_resolution // 60)
            minutes = int(avg_resolution % 60)
            avg_resolution_display = f"{hours}h {minutes}m"
        
        # Most common category
        most_common = Ticket.objects.values('category__name').annotate(
            count=Count('id')
        ).order_by('-count').first()
        
        most_common_category = most_common['category__name'] if most_common else "No data"
        
        # Recent tickets
        recent_tickets = Ticket.objects.select_related(
            'category', 'created_by', 'assigned_to'
        ).order_by('-created_at')[:10]
        
        dashboard_data = {
            'total_tickets': total_tickets,
            'open_tickets': open_tickets,
            'in_progress_tickets': in_progress_tickets,
            'resolved_today': resolved_today,
            'my_tickets': my_tickets,
            'avg_resolution_time': avg_resolution_display,
            'most_common_category': most_common_category,
            'recent_tickets': recent_tickets
        }
        
        serializer = DashboardStatsSerializer(dashboard_data)
        return Response(serializer.data)


class SolutionViewSet(viewsets.ModelViewSet):
    queryset = Solution.objects.all()  # Add base queryset
    permission_classes = [permissions.AllowAny]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return SolutionListSerializer
        else:
            return SolutionDetailSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset().filter(is_active=True).select_related('category', 'created_by')
        
        # Filter by category
        category_id = self.request.query_params.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        # Search in title, description, and keywords
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(keywords__icontains=search)
            )
        
        # Sort by success rate by default
        return queryset.annotate(
            success_rate_calc=F('times_successful') * 100.0 / F('times_suggested')
        ).order_by('-success_rate_calc', '-times_successful')
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=False, methods=['get'])
    def top_solutions(self, request):
        """Get top performing solutions"""
        solutions = Solution.objects.filter(
            is_active=True,
            times_suggested__gte=5  # Only include solutions tried at least 5 times
        ).annotate(
            success_rate_calc=F('times_successful') * 100.0 / F('times_suggested')
        ).order_by('-success_rate_calc')[:10]
        
        serializer = SolutionListSerializer(solutions, many=True)
        return Response(serializer.data)


class PatternViewSet(viewsets.ModelViewSet):
    queryset = TicketPattern.objects.filter(is_active=True)
    serializer_class = TicketPatternSerializer
    permission_classes = [permissions.AllowAny]
    
    @action(detail=False, methods=['post'])
    def analyze_patterns(self, request):
        """Trigger pattern analysis"""
        analyzer = PatternAnalyzer()
        results = analyzer.analyze_recent_tickets()
        
        return Response({
            'message': 'Pattern analysis completed',
            'patterns_found': results.get('patterns_found', 0),
            'tickets_analyzed': results.get('tickets_analyzed', 0)
        })


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.filter(is_active=True)
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]
    
    @action(detail=False, methods=['get'])
    def technicians(self, request):
        """Get list of users who can be assigned tickets"""
        # You might want to filter this based on groups or permissions
        technicians = User.objects.filter(
            is_active=True,
            is_staff=True  # Or based on specific groups
        ).order_by('first_name', 'last_name')
        
        serializer = self.get_serializer(technicians, many=True)
        return Response(serializer.data)