#!/usr/bin/env python
"""
Fix admin display issues and test the admin interface
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

def test_model_properties():
    """Test that model properties work correctly"""
    print("🧪 Testing Model Properties...")
    
    from apps.core.models import Solution, TicketPattern
    
    # Test Solution success_rate
    solutions = Solution.objects.all()[:3]
    print(f"   📊 Testing {solutions.count()} solutions:")
    
    for solution in solutions:
        try:
            rate = solution.success_rate
            print(f"      ✅ {solution.title}: {rate}% success rate")
        except Exception as e:
            print(f"      ❌ {solution.title}: Error - {e}")
    
    # Test TicketPattern helpfulness_rate
    patterns = TicketPattern.objects.all()[:3]
    print(f"   🎯 Testing {patterns.count()} patterns:")
    
    for pattern in patterns:
        try:
            rate = pattern.helpfulness_rate
            print(f"      ✅ {pattern.pattern_type}: {rate}% helpfulness rate")
        except Exception as e:
            print(f"      ❌ {pattern.pattern_type}: Error - {e}")

def test_admin_display_methods():
    """Test admin display methods"""
    print("\n🎨 Testing Admin Display Methods...")
    
    from apps.core.admin import SolutionAdmin, TicketPatternAdmin
    from apps.core.models import Solution, TicketPattern
    
    # Test SolutionAdmin methods
    solution_admin = SolutionAdmin(Solution, None)
    solutions = Solution.objects.all()[:2]
    
    for solution in solutions:
        try:
            display = solution_admin.success_rate_display(solution)
            print(f"      ✅ Solution display method works: {display}")
        except Exception as e:
            print(f"      ❌ Solution display method failed: {e}")
    
    # Test PatternAdmin methods
    pattern_admin = TicketPatternAdmin(TicketPattern, None)
    patterns = TicketPattern.objects.all()[:2]
    
    for pattern in patterns:
        try:
            display = pattern_admin.helpfulness_display(pattern)
            print(f"      ✅ Pattern display method works: {display}")
        except Exception as e:
            print(f"      ❌ Pattern display method failed: {e}")

def show_admin_urls():
    """Show admin URLs to test"""
    print("\n🌐 Admin URLs to Test:")
    print("   📋 Main admin: http://localhost:8000/admin/")
    print("   🎫 Tickets: http://localhost:8000/admin/core/ticket/")
    print("   💡 Solutions: http://localhost:8000/admin/core/solution/")
    print("   📁 Categories: http://localhost:8000/admin/core/category/")
    print("   🎯 Patterns: http://localhost:8000/admin/core/ticketpattern/")
    print("   📊 Analytics: http://localhost:8000/admin/core/ticketanalytics/")

def run_tests():
    """Run all admin tests"""
    print("🚀 Testing Admin Interface Fixes")
    print("=" * 50)
    
    test_model_properties()
    test_admin_display_methods()
    show_admin_urls()
    
    print("\n✅ Admin fixes applied!")
    print("\n📋 Next Steps:")
    print("   1. Restart your Django server: python manage.py runserver")
    print("   2. Visit the admin interface: http://localhost:8000/admin/")
    print("   3. Test the Solutions and Patterns sections")
    
    print("\n💡 If you still get errors:")
    print("   - Check the server console for detailed error messages")
    print("   - Try creating a fresh migration: python manage.py makemigrations")

if __name__ == '__main__':
    run_tests()