#!/usr/bin/env python
"""
Temporarily make API public for testing
Run this, test the API, then restore authentication
"""

import fileinput
import sys
from pathlib import Path

def make_api_public():
    """Temporarily remove authentication requirement"""
    print("🔓 Making API public for testing...")
    
    api_views_file = Path('apps/core/api_views.py')
    
    if not api_views_file.exists():
        print("❌ api_views.py not found")
        return
    
    # Read the file
    content = api_views_file.read_text()
    
    # Replace authentication requirement with allow all
    updated_content = content.replace(
        'permission_classes = [permissions.IsAuthenticated]',
        'permission_classes = [permissions.AllowAny]  # TESTING ONLY!'
    )
    
    # Write back
    api_views_file.write_text(updated_content)
    
    print("✅ API is now public for testing")
    print("⚠️  Remember to restore authentication when done!")
    print("🔧 Restart the server: python manage.py runserver")

def restore_authentication():
    """Restore authentication requirement"""
    print("🔒 Restoring API authentication...")
    
    api_views_file = Path('apps/core/api_views.py')
    
    if not api_views_file.exists():
        print("❌ api_views.py not found")
        return
    
    # Read the file
    content = api_views_file.read_text()
    
    # Restore authentication requirement
    updated_content = content.replace(
        'permission_classes = [permissions.AllowAny]  # TESTING ONLY!',
        'permission_classes = [permissions.IsAuthenticated]'
    )
    
    # Write back
    api_views_file.write_text(updated_content)
    
    print("✅ API authentication restored")
    print("🔧 Restart the server: python manage.py runserver")

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'restore':
        restore_authentication()
    else:
        make_api_public()
        print("\n📋 To restore authentication later, run:")
        print("   python make_api_public_for_testing.py restore")