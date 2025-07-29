#!/usr/bin/env python
"""
Test ViewSet configuration
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

def test_viewsets():
    """Test that all ViewSets have proper queryset attributes"""
    print("🔧 Testing ViewSet Configuration...")
    
    try:
        from apps.core.api_views import (
            CategoryViewSet, TicketViewSet, SolutionViewSet, 
            PatternViewSet, UserViewSet
        )
        
        viewsets = [
            ('CategoryViewSet', CategoryViewSet),
            ('TicketViewSet', TicketViewSet),
            ('SolutionViewSet', SolutionViewSet),
            ('PatternViewSet', PatternViewSet),
            ('UserViewSet', UserViewSet),
        ]
        
        all_good = True
        
        for name, viewset_class in viewsets:
            # Check if queryset attribute exists
            if hasattr(viewset_class, 'queryset'):
                print(f"   ✅ {name} has queryset attribute")
                
                # Try to evaluate the queryset
                try:
                    queryset = viewset_class.queryset
                    count = queryset.count()
                    print(f"      📊 Query works: {count} objects found")
                except Exception as e:
                    print(f"      ⚠️  Query error: {e}")
                    
            else:
                print(f"   ❌ {name} missing queryset attribute")
                all_good = False
        
        return all_good
        
    except ImportError as e:
        print(f"   ❌ Import error: {e}")
        return False

def test_router_registration():
    """Test that the router can register all ViewSets"""
    print("\n🔗 Testing Router Registration...")
    
    try:
        from rest_framework.routers import DefaultRouter
        from apps.core.api_views import (
            CategoryViewSet, TicketViewSet, SolutionViewSet, 
            PatternViewSet, UserViewSet
        )
        
        router = DefaultRouter()
        
        viewsets_to_register = [
            ('categories', CategoryViewSet),
            ('tickets', TicketViewSet),
            ('solutions', SolutionViewSet),
            ('patterns', PatternViewSet),
            ('users', UserViewSet),
        ]
        
        for prefix, viewset_class in viewsets_to_register:
            try:
                router.register(prefix, viewset_class)
                print(f"   ✅ {prefix} -> {viewset_class.__name__} registered successfully")
            except Exception as e:
                print(f"   ❌ {prefix} -> {viewset_class.__name__} failed: {e}")
                return False
        
        # Get URL patterns
        urls = router.urls
        print(f"   📋 Generated {len(urls)} URL patterns")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Router registration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_tests():
    """Run all ViewSet tests"""
    print("🚀 Running ViewSet Configuration Tests")
    print("=" * 50)
    
    viewsets_ok = test_viewsets()
    router_ok = test_router_registration()
    
    print("\n" + "=" * 50)
    if viewsets_ok and router_ok:
        print("🎉 ALL TESTS PASSED!")
        print("\n✅ ViewSets are properly configured")
        print("✅ Router registration works")
        print("\n🔧 Now try starting the server:")
        print("   python manage.py runserver")
    else:
        print("❌ Some tests failed")
        if not viewsets_ok:
            print("   - ViewSet configuration issues")
        if not router_ok:
            print("   - Router registration issues")

if __name__ == '__main__':
    run_tests()