#!/usr/bin/env python
"""
Quick fix script for decimal arithmetic and timezone issues
Run this from your Django project root directory
"""

import os
import sys
import django
from pathlib import Path
from decimal import Decimal

# Add the project root to Python path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.core.models import Solution, TicketPattern

def fix_decimal_fields():
    """Fix any existing decimal field issues"""
    print("🔧 Checking and fixing decimal field issues...")
    
    # Check solutions
    solutions = Solution.objects.all()
    print(f"   📊 Found {solutions.count()} solutions")
    
    for solution in solutions:
        # Test success_rate calculation
        try:
            rate = solution.success_rate
            print(f"   ✅ Solution '{solution.title}': {rate}% success rate")
        except Exception as e:
            print(f"   ❌ Error with solution '{solution.title}': {e}")
    
    # Check patterns
    patterns = TicketPattern.objects.all()
    print(f"   📊 Found {patterns.count()} patterns")
    
    for pattern in patterns:
        try:
            confidence = float(pattern.confidence_score)
            print(f"   ✅ Pattern '{pattern.pattern_type}': {confidence}% confidence")
        except Exception as e:
            print(f"   ❌ Error with pattern '{pattern.pattern_type}': {e}")

def test_solution_engine():
    """Test the solution suggestion engine"""
    print("\n💡 Testing Solution Suggestion Engine...")
    
    from apps.core.models import Ticket
    from apps.core.utils import SolutionSuggestionEngine
    
    # Get a test ticket
    ticket = Ticket.objects.first()
    if not ticket:
        print("   ⚠️  No tickets found to test with")
        return
    
    print(f"   🎫 Testing with ticket: {ticket.title}")
    
    try:
        engine = SolutionSuggestionEngine()
        suggestions = engine.suggest_solutions(ticket)
        print(f"   ✅ Found {len(suggestions)} suggestions")
        
        for i, suggestion in enumerate(suggestions[:3]):
            print(f"      {i+1}. {suggestion['solution'].title} ({suggestion['confidence_score']:.2f})")
            
    except Exception as e:
        print(f"   ❌ Error in suggestion engine: {e}")
        import traceback
        traceback.print_exc()

def run_fixes():
    """Run all fixes"""
    print("🚀 Running Decimal and Timezone Fixes")
    print("=" * 50)
    
    fix_decimal_fields()
    test_solution_engine()
    
    print("\n✅ All fixes completed!")
    print("\n📋 Next steps:")
    print("1. Try running: python test_ticket_system.py")
    print("2. Try running: python manage.py create_sample_data")

if __name__ == '__main__':
    run_fixes()