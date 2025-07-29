#!/usr/bin/env python
"""
Clean up problematic data and test the fixes
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

from apps.core.models import Ticket, Solution, Category, TicketComment, TicketSolution, TicketPattern
from django.contrib.auth.models import User

def cleanup_data():
    """Clean up any problematic test data"""
    print("🧹 Cleaning up existing test data...")
    
    # Count existing data
    ticket_count = Ticket.objects.count()
    solution_count = Solution.objects.count()
    category_count = Category.objects.count()
    
    print(f"   📊 Current data: {ticket_count} tickets, {solution_count} solutions, {category_count} categories")
    
    # Optional: Clean up test data (uncomment if you want to start fresh)
    # print("   🗑️  Removing test tickets...")
    # Ticket.objects.filter(title__contains='Test').delete()
    # Ticket.objects.filter(title__contains='#').delete()
    
    print("   ✅ Cleanup completed")

def test_timezone_fix():
    """Test that timezone handling is working"""
    print("\n🕐 Testing timezone handling...")
    
    from django.utils import timezone
    from datetime import timedelta
    
    # Get or create a test user
    user, created = User.objects.get_or_create(
        username='test_timezone_user',
        defaults={'email': 'test@example.com'}
    )
    
    # Get or create a test category
    category, created = Category.objects.get_or_create(
        name='Test Timezone Category',
        defaults={'description': 'Testing timezone handling', 'color': '#blue'}
    )
    
    try:
        # Create a ticket with timezone-aware dates
        now = timezone.now()
        past_date = now - timedelta(days=1)
        
        ticket = Ticket.objects.create(
            title="Timezone Test Ticket",
            description="Testing timezone handling",
            category=category,
            priority="MEDIUM",
            created_by=user,
            status="RESOLVED"
        )
        
        # Update the created_at and resolved_at
        ticket.created_at = past_date
        ticket.resolved_at = now
        ticket.save()  # This should not fail now
        
        print(f"   ✅ Ticket created successfully with resolution time: {ticket.resolution_time_minutes} minutes")
        
        # Clean up test ticket
        ticket.delete()
        
    except Exception as e:
        print(f"   ❌ Timezone test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def test_sample_data_creation():
    """Test creating a small amount of sample data"""
    print("\n📋 Testing sample data creation...")
    
    try:
        import subprocess
        result = subprocess.run(
            ['python', 'manage.py', 'create_sample_data', '--tickets', '5', '--solutions', '3'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print("   ✅ Sample data creation test passed")
            print(f"   📊 Final counts:")
            print(f"      Tickets: {Ticket.objects.count()}")
            print(f"      Solutions: {Solution.objects.count()}")
            print(f"      Categories: {Category.objects.count()}")
            return True
        else:
            print("   ❌ Sample data creation failed")
            print(f"   Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"   ❌ Sample data test failed: {e}")
        return False

def run_all_tests():
    """Run all tests"""
    print("🚀 Running Cleanup and Timezone Fix Tests")
    print("=" * 50)
    
    cleanup_data()
    
    timezone_ok = test_timezone_fix()
    if timezone_ok:
        sample_data_ok = test_sample_data_creation()
    else:
        sample_data_ok = False
    
    print("\n" + "=" * 50)
    if timezone_ok and sample_data_ok:
        print("🎉 ALL TESTS PASSED!")
        print("\n📋 You can now safely run:")
        print("   python manage.py create_sample_data")
        print("   python test_ticket_system.py")
        print("   python manage.py runserver")
    else:
        print("❌ Some tests failed. Check the errors above.")
        if not timezone_ok:
            print("   - Timezone handling needs fixing")
        if not sample_data_ok:
            print("   - Sample data creation needs fixing")

if __name__ == '__main__':
    run_all_tests()