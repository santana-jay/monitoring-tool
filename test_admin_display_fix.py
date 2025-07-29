#!/usr/bin/env python
"""
Test the admin display fix
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

def test_fixed_admin_display():
    """Test that the admin display methods now work"""
    print("🧪 Testing Fixed Admin Display Methods...")
    
    from apps.core.admin import SolutionAdmin
    from apps.core.models import Solution
    
    admin_instance = SolutionAdmin(Solution, None)
    solutions = Solution.objects.all()[:5]
    
    print("\n📊 Solution Success Rate Displays:")
    for solution in solutions:
        try:
            display_result = admin_instance.success_rate_display(solution)
            rate = solution.success_rate
            print(f"   ✅ {solution.title}: {rate:.1f}% -> {display_result}")
        except Exception as e:
            print(f"   ❌ {solution.title}: Error - {e}")
    
    # Test patterns too if any exist
    from apps.core.models import TicketPattern
    from apps.core.admin import TicketPatternAdmin
    
    patterns = TicketPattern.objects.all()[:3]
    if patterns:
        print("\n🎯 Pattern Helpfulness Rate Displays:")
        pattern_admin = TicketPatternAdmin(TicketPattern, None)
        
        for pattern in patterns:
            try:
                display_result = pattern_admin.helpfulness_display(pattern)
                rate = pattern.helpfulness_rate
                print(f"   ✅ {pattern.pattern_type}: {rate:.1f}% -> {display_result}")
            except Exception as e:
                print(f"   ❌ {pattern.pattern_type}: Error - {e}")
    else:
        print("\n🎯 No patterns found to test")

def run_test():
    """Run the display test"""
    print("🚀 Testing Admin Display Fixes")
    print("=" * 50)
    
    test_fixed_admin_display()
    
    print("\n✅ Testing complete!")
    print("\n📋 Next Steps:")
    print("   1. Restart Django server: python manage.py runserver")
    print("   2. Refresh the Solutions admin page")
    print("   3. You should see colored percentages instead of 'N/A'")
    print("   4. Expected colors:")
    print("      🟢 Green: ≥70% success rate")
    print("      🟠 Orange: 40-69% success rate") 
    print("      🔴 Red: <40% success rate")

if __name__ == '__main__':
    run_test()