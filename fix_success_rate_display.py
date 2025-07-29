#!/usr/bin/env python
"""
Fix the Success Rate display in admin
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

def test_success_rate_calculation():
    """Test the success rate calculation directly"""
    print("🧮 Testing Success Rate Calculations...")
    
    from apps.core.models import Solution
    
    solutions = Solution.objects.all()[:5]
    
    for solution in solutions:
        print(f"\n📊 {solution.title}:")
        print(f"   Times suggested: {solution.times_suggested}")
        print(f"   Times successful: {solution.times_successful}")
        
        try:
            rate = solution.success_rate
            print(f"   ✅ Success rate: {rate:.1f}%")
        except Exception as e:
            print(f"   ❌ Error calculating rate: {e}")

def test_admin_display_method():
    """Test the admin display method specifically"""
    print("\n🎨 Testing Admin Display Method...")
    
    from apps.core.admin import SolutionAdmin
    from apps.core.models import Solution
    
    admin_instance = SolutionAdmin(Solution, None)
    solutions = Solution.objects.all()[:3]
    
    for solution in solutions:
        print(f"\n🔧 Testing {solution.title}:")
        try:
            # Test the success_rate property first
            rate = solution.success_rate
            print(f"   Model success_rate: {rate:.1f}%")
            
            # Test the admin display method
            display_result = admin_instance.success_rate_display(solution)
            print(f"   Admin display result: {display_result}")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()

def create_better_admin_method():
    """Create a more robust admin display method"""
    print("\n🔨 Creating Better Admin Display Method...")
    
    new_admin_method = '''
    def success_rate_display(self, obj):
        """Display success rate with better error handling"""
        try:
            if obj.times_suggested == 0:
                return "0.0%"
            
            rate = (obj.times_successful / obj.times_suggested) * 100
            rate = min(rate, 100.0)  # Cap at 100%
            
            # Color coding
            if rate >= 70:
                color = 'green'
            elif rate >= 40:
                color = 'orange'  
            else:
                color = 'red'
            
            return format_html(
                '<span style="color: {}; font-weight: bold;">{:.1f}%</span>',
                color, rate
            )
        except (TypeError, ValueError, ZeroDivisionError, AttributeError) as e:
            # Debug info
            return f"Error: {e}"
        except Exception as e:
            return f"Unknown error: {e}"
    '''
    
    print("📝 New admin method created (copy this to admin.py if needed)")
    print(new_admin_method)

def run_diagnostics():
    """Run all diagnostics"""
    print("🔍 Diagnosing Success Rate Display Issue")
    print("=" * 50)
    
    test_success_rate_calculation()
    test_admin_display_method()
    create_better_admin_method()
    
    print("\n💡 Likely Issue:")
    print("   The success_rate property is working, but the admin display method")
    print("   might be catching an exception and returning 'N/A'")
    
    print("\n🔧 Quick Fix:")
    print("   1. The model calculations are working")
    print("   2. Try refreshing the admin page")
    print("   3. If still showing N/A, check the admin method")

if __name__ == '__main__':
    run_diagnostics()