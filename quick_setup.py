#!/usr/bin/env python
"""
Quick setup script for IT Help Desk Ticket System
Run this after setting up the environment
"""

import os
import sys
import subprocess
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        if e.stdout:
            print(f"   STDOUT: {e.stdout}")
        if e.stderr:
            print(f"   STDERR: {e.stderr}")
        return False

def setup_project():
    """Set up the Django ticket system project"""
    print("🎫 Setting up IT Help Desk Ticket System")
    print("=" * 50)
    
    # Create management command directories
    management_dirs = [
        "apps/core/management",
        "apps/core/management/commands",
        "logs"  # For loguru logs
    ]
    
    for dir_path in management_dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        if 'management' in dir_path:
            Path(f"{dir_path}/__init__.py").touch()
    
    print("📁 Created management directories")
    
    # Run Django setup commands
    commands = [
        ("python manage.py makemigrations", "Creating migrations"),
        ("python manage.py migrate", "Running migrations"),
        ("python manage.py collectstatic --noinput", "Collecting static files"),
    ]
    
    for command, description in commands:
        if not run_command(command, description):
            return False
    
    # Test the ticket system
    print("\n🧪 Testing ticket system...")
    if run_command("python test_ticket_system.py", "Testing ticket system"):
        print("✅ Ticket system is working!")
    else:
        print("⚠️  Ticket system test failed - check the logs")
    
    print("\n🎉 Setup complete!")
    print("\n📋 Next steps:")
    print("1. Create superuser: python manage.py createsuperuser")
    print("2. Create sample data: python manage.py create_sample_data")
    print("3. Start server: python manage.py runserver")
    print("4. Visit admin: http://localhost:8000/admin/")
    print("5. Check API endpoints:")
    print("   - Dashboard: http://localhost:8000/api/tickets/dashboard/")
    print("   - Tickets: http://localhost:8000/api/tickets/")
    print("   - Solutions: http://localhost:8000/api/solutions/")
    print("   - Categories: http://localhost:8000/api/categories/")
    print("6. Analyze patterns: python manage.py analyze_patterns")
    
    return True

if __name__ == '__main__':
    setup_project()