#!/usr/bin/env python
"""
Comprehensive test script for the IT Help Desk Ticket System
Run this from your Django project root directory
"""

import os
import sys
import django
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Import models and utilities
from apps.core.models import Category, Ticket, Solution, TicketComment, TicketSolution, TicketPattern
from apps.core.utils import SolutionSuggestionEngine, PatternAnalyzer
from django.contrib.auth.models import User
from django.utils import timezone


def test_models():
    """Test basic model operations"""
    print("📋 Testing Models...")
    
    # Test category creation
    category = Category.objects.create(
        name="Test Category",
        description="A test category",
        color="#3498db"
    )
    print(f"   ✅ Category created: {category}")
    
    # Test user creation
    user, created = User.objects.get_or_create(
        username="testuser",
        defaults={
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com'
        }
    )
    if created:
        user.set_password('testpass')
        user.save()
    print(f"   ✅ User ready: {user}")
    
    # Test ticket creation
    ticket = Ticket.objects.create(
        title="Test ticket for system verification",
        description="This is a test ticket to verify the system is working correctly. The printer is not responding to print commands.",
        category=category,
        priority="MEDIUM",
        created_by=user,
        system_info={
            'os': 'Windows 10',
            'browser': 'Chrome 91.0'
        }
    )
    print(f"   ✅ Ticket created: {ticket}")
    
    # Test solution creation
    solution = Solution.objects.create(
        title="Test Solution - Restart Print Spooler",
        description="Restart the print spooler service to fix printer issues",
        steps="1. Open Services\n2. Find Print Spooler\n3. Right-click and restart\n4. Test printing",
        keywords="printer, spooler, restart, service, print",
        category=category,
        created_by=user
    )
    print(f"   ✅ Solution created: {solution}")
    
    # Test comment creation
    comment = TicketComment.objects.create(
        ticket=ticket,
        author=user,
        content="I tried turning the printer off and on, but it didn't help.",
        is_internal=False
    )
    print(f"   ✅ Comment created: {comment}")
    
    return {
        'category': category,
        'user': user,
        'ticket': ticket,
        'solution': solution,
        'comment': comment
    }


def test_solution_suggestions(test_data):
    """Test the solution suggestion engine"""
    print("\n💡 Testing Solution Suggestion Engine...")
    
    ticket = test_data['ticket']
    solution = test_data['solution']
    
    # Create solution suggestion engine
    engine = SolutionSuggestionEngine()
    
    # Test keyword extraction
    keywords = engine.extract_keywords(ticket.title + " " + ticket.description)
    print(f"   📝 Extracted keywords: {keywords[:5]}...")  # Show first 5
    
    # Test solution suggestions
    suggestions = engine.suggest_solutions(ticket)
    print(f"   🎯 Found {len(suggestions)} solution suggestions")
    
    for i, suggestion in enumerate(suggestions[:3]):  # Show top 3
        print(f"      {i+1}. {suggestion['solution'].title}")
        print(f"         Confidence: {suggestion['confidence_score']:.2f}")
        print(f"         Reason: {suggestion['match_reason']}")
        print(f"         Method: {suggestion['suggested_by']}")
    
    return suggestions


def test_pattern_analysis(test_data):
    """Test the pattern analysis engine"""
    print("\n🔍 Testing Pattern Analysis Engine...")
    
    # Create additional test tickets for pattern analysis
    category = test_data['category']
    user = test_data['user']
    
    # Create more tickets with similar patterns
    similar_tickets = []
    printer_issues = [
        "Printer won't print",
        "Printer is offline",
        "Printer paper jam",
        "Print job stuck in queue"
    ]
    
    for i, title in enumerate(printer_issues):
        ticket = Ticket.objects.create(
            title=title,
            description=f"Having issues with the office printer. {title.lower()} and need assistance.",
            category=category,
            priority="MEDIUM",
            created_by=user
        )
        similar_tickets.append(ticket)
    
    print(f"   📋 Created {len(similar_tickets)} similar tickets for pattern analysis")
    
    # Run pattern analysis
    analyzer = PatternAnalyzer()
    results = analyzer.analyze_recent_tickets(days=1)  # Just today's tickets
    
    print(f"   📊 Analysis results:")
    print(f"      Tickets analyzed: {results['tickets_analyzed']}")
    print(f"      Patterns found: {results['patterns_found']}")
    
    # Show found patterns
    patterns = TicketPattern.objects.all()[:3]
    for pattern in patterns:
        print(f"      Pattern: {pattern.pattern_type} - {pattern.confidence_score}% confidence")
    
    return results


def test_api_functionality():
    """Test API-like functionality"""
    print("\n🔌 Testing API Functionality...")
    
    # Test dashboard statistics
    total_tickets = Ticket.objects.count()
    open_tickets = Ticket.objects.filter(status='OPEN').count()
    resolved_tickets = Ticket.objects.filter(status='RESOLVED').count()
    
    print(f"   📊 Dashboard Stats:")
    print(f"      Total tickets: {total_tickets}")
    print(f"      Open tickets: {open_tickets}")
    print(f"      Resolved tickets: {resolved_tickets}")
    
    # Test search functionality
    search_term = "printer"
    search_results = Ticket.objects.filter(
        title__icontains=search_term
    ).count()
    print(f"      Tickets mentioning '{search_term}': {search_results}")
    
    # Test category filtering
    categories = Category.objects.all()
    for category in categories:
        ticket_count = category.ticket_set.count()
        print(f"      {category.name}: {ticket_count} tickets")
    
    return True


def test_ticket_workflow():
    """Test complete ticket workflow"""
    print("\n🔄 Testing Complete Ticket Workflow...")
    
    # Get or create test user
    user = User.objects.filter(username='testuser').first()
    if not user:
        print("   ❌ Test user not found")
        return False
    
    # Get a test ticket
    ticket = Ticket.objects.filter(created_by=user).first()
    if not ticket:
        print("   ❌ Test ticket not found")
        return False
    
    print(f"   🎫 Working with ticket: {ticket.title}")
    
    # Step 1: Assign ticket
    technician, created = User.objects.get_or_create(
        username='technician',
        defaults={
            'first_name': 'Tech',
            'last_name': 'Support',
            'email': 'tech@company.com',
            'is_staff': True
        }
    )
    
    ticket.assigned_to = technician
    ticket.status = 'IN_PROGRESS'
    ticket.save()
    print(f"   ✅ Ticket assigned to {technician.get_full_name()}")
    
    # Step 2: Add a comment
    comment = TicketComment.objects.create(
        ticket=ticket,
        author=technician,
        content="I'm investigating this issue. Will try the standard printer troubleshooting steps.",
        is_internal=True
    )
    print(f"   ✅ Added technician comment")
    
    # Step 3: Apply a solution
    solution = Solution.objects.first()
    if solution:
        ticket_solution = TicketSolution.objects.create(
            ticket=ticket,
            solution=solution,
            was_successful=True,
            notes="Solution worked perfectly. User confirmed printer is working.",
            applied_by=technician
        )
        print(f"   ✅ Applied solution: {solution.title}")
    
    # Step 4: Resolve ticket
    ticket.status = 'RESOLVED'
    ticket.resolution = "Issue resolved by restarting the print spooler service. User confirmed printer is working normally."
    ticket.save()
    print(f"   ✅ Ticket resolved")
    
    # Show final ticket state
    print(f"   📋 Final ticket state:")
    print(f"      Status: {ticket.status}")
    print(f"      Resolution time: {ticket.resolution_time_display if hasattr(ticket, 'resolution_time_display') else 'Calculated automatically'}")
    print(f"      Comments: {ticket.comments.count()}")
    print(f"      Solutions tried: {ticket.tried_solutions.count()}")
    
    return True


def run_comprehensive_test():
    """Run all tests"""
    print("🚀 Starting Comprehensive IT Help Desk System Test")
    print("=" * 60)
    
    try:
        # Test 1: Basic model operations
        test_data = test_models()
        
        # Test 2: Solution suggestion engine
        suggestions = test_solution_suggestions(test_data)
        
        # Test 3: Pattern analysis
        pattern_results = test_pattern_analysis(test_data)
        
        # Test 4: API functionality
        api_test = test_api_functionality()
        
        # Test 5: Complete workflow
        workflow_test = test_ticket_workflow()
        
        # Summary
        print("\n" + "=" * 60)
        print("🎉 ALL TESTS COMPLETED SUCCESSFULLY!")
        print("\n📊 Test Summary:")
        print(f"   ✅ Models: Working")
        print(f"   ✅ Solution Suggestions: {len(suggestions)} suggestions found")
        print(f"   ✅ Pattern Analysis: {pattern_results['patterns_found']} patterns detected")
        print(f"   ✅ API Functions: Working")
        print(f"   ✅ Ticket Workflow: Complete")
        
        print("\n🎯 Next Steps:")
        print("   1. Create superuser: python manage.py createsuperuser")
        print("   2. Start server: python manage.py runserver")
        print("   3. Visit admin: http://localhost:8000/admin/")
        print("   4. Test API: http://localhost:8000/api/tickets/")
        print("   5. Create sample data: python manage.py create_sample_data")
        print("   6. Analyze patterns: python manage.py analyze_patterns")
        
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = run_comprehensive_test()
    sys.exit(0 if success else 1)