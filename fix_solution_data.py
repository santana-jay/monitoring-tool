#!/usr/bin/env python
"""
Fix solution data where times_successful > times_suggested
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

def fix_solution_statistics():
    """Fix solutions where times_successful > times_suggested"""
    print("🔧 Fixing Solution Statistics...")
    
    from apps.core.models import Solution
    
    solutions = Solution.objects.all()
    fixed_count = 0
    
    for solution in solutions:
        if solution.times_successful > solution.times_suggested:
            print(f"   🔄 Fixing {solution.title}:")
            print(f"      Before: {solution.times_successful}/{solution.times_suggested} = {solution.success_rate:.1f}%")
            
            # Fix: ensure times_successful <= times_suggested
            # We'll keep times_suggested and adjust times_successful
            if solution.times_suggested == 0:
                solution.times_suggested = max(solution.times_successful, 10)
            
            # Ensure times_successful is reasonable
            solution.times_successful = min(solution.times_successful, solution.times_suggested)
            
            # Make sure we have reasonable minimums
            if solution.times_suggested < 5:
                solution.times_suggested = 10
                solution.times_successful = min(solution.times_successful, 8)
            
            solution.save()
            
            print(f"      After:  {solution.times_successful}/{solution.times_suggested} = {solution.success_rate:.1f}%")
            fixed_count += 1
    
    print(f"   ✅ Fixed {fixed_count} solutions")
    
    # Show some examples
    print("\n📊 Sample Success Rates After Fix:")
    for solution in solutions[:5]:
        print(f"   {solution.title}: {solution.success_rate:.1f}% ({solution.times_successful}/{solution.times_suggested})")

def test_admin_after_fix():
    """Test admin display methods after fixing data"""
    print("\n🎨 Testing Admin Methods After Fix...")
    
    from apps.core.admin import SolutionAdmin
    from apps.core.models import Solution
    
    solution_admin = SolutionAdmin(Solution, None)
    solutions = Solution.objects.all()[:3]
    
    for solution in solutions:
        try:
            display = solution_admin.success_rate_display(solution)
            print(f"   ✅ {solution.title}: {display}")
        except Exception as e:
            print(f"   ❌ {solution.title}: Error - {e}")

def run_fix():
    """Run all fixes"""
    print("🚀 Fixing Solution Data Issues")
    print("=" * 50)
    
    fix_solution_statistics()
    test_admin_after_fix()
    
    print("\n✅ Solution data fixed!")
    print("\n📋 Next Steps:")
    print("   1. Restart Django server: python manage.py runserver")
    print("   2. Visit Solutions admin: http://localhost:8000/admin/core/solution/")
    print("   3. Success rates should now be ≤ 100%")

if __name__ == '__main__':
    run_fix()