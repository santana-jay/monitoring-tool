from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

def api_health(request):
    """Simple health check endpoint"""
    return JsonResponse({
        'status': 'healthy',
        'service': 'IT Help Desk API',
        'version': '1.0.0'
    })

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', api_health, name='health'),
    path('', include('apps.core.urls')),  # This includes our API routes
]