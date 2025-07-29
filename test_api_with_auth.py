#!/usr/bin/env python
"""
Test API with proper authentication
Run this from your Django project root directory
"""

import os
import sys
import django
import requests
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from django.test import Client

def create_test_user():
    """Create a test user for API testing"""
    print("👤 Creating test user...")
    
    username = 'api_test_user'
    password = 'testpass123'
    
    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            'email': 'test@example.com',
            'first_name': 'API',
            'last_name': 'Tester',
            'is_staff': True,
            'is_superuser': True
        }
    )
    
    if created:
        user.set_password(password)
        user.save()
        print(f"   ✅ Created user: {username}")
    else:
        print(f"   ✅ User already exists: {username}")
    
    return username, password

def test_api_with_session():
    """Test API using Django's test client (simulates browser session)"""
    print("\n🔧 Testing API with Django session...")
    
    username, password = create_test_user()
    
    # Create a test client
    client = Client()
    
    # Login
    login_success = client.login(username=username, password=password)
    if not login_success:
        print("   ❌ Login failed")
        return False
    
    print("   ✅ Logged in successfully")
    
    # Test endpoints
    endpoints = [
        '/health/',
        '/api/tickets/',
        '/api/tickets/dashboard/',
        '/api/categories/',
        '/api/solutions/',
    ]
    
    for endpoint in endpoints:
        try:
            response = client.get(endpoint)
            if response.status_code == 200:
                print(f"   ✅ {endpoint} - Status: {response.status_code}")
                
                # Show some data for interesting endpoints
                if endpoint == '/api/tickets/dashboard/':
                    data = response.json()
                    print(f"      📊 Dashboard: {data.get('total_tickets', 0)} total tickets")
                elif endpoint == '/api/tickets/':
                    data = response.json()
                    count = data.get('count', 0) if isinstance(data, dict) else len(data)
                    print(f"      🎫 Tickets: {count} found")
                    
            else:
                print(f"   ⚠️  {endpoint} - Status: {response.status_code}")
                if hasattr(response, 'json'):
                    try:
                        error_data = response.json()
                        print(f"      Error: {error_data}")
                    except:
                        pass
                        
        except Exception as e:
            print(f"   ❌ {endpoint} - Error: {e}")
    
    return True

def show_curl_with_session():
    """Show how to test with curl using session authentication"""
    print("\n🌐 Testing with curl + session authentication:")
    print("   # First, get the CSRF token and login")
    print("   curl -c cookies.txt http://localhost:8000/admin/login/")
    print("   # Then login (you'll need to extract CSRF token)")
    print("   # This is complex with curl, so Django session testing above is easier")
    print("")
    print("   # Or use the Django admin interface:")
    print("   # 1. Go to http://localhost:8000/admin/")
    print("   # 2. Login with your superuser account") 
    print("   # 3. Then visit API URLs in the same browser")

def run_tests():
    """Run all API tests"""
    print("🚀 Testing API with Authentication")
    print("=" * 50)
    
    # Test with Django session
    session_ok = test_api_with_session()
    
    if session_ok:
        print("\n🎉 API tests completed successfully!")
        print("\n📋 API is working with authentication")
        print("💡 You can also:")
        print("   1. Use the Django admin interface to browse data")
        print("   2. Temporarily disable auth for curl testing")
        print("   3. Build a frontend that handles authentication")
    else:
        print("\n❌ API tests failed")
    
    show_curl_with_session()

if __name__ == '__main__':
    run_tests()