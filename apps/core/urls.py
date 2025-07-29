from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views

# Create router and register viewsets
router = DefaultRouter()
router.register(r'categories', api_views.CategoryViewSet)
router.register(r'tickets', api_views.TicketViewSet)
router.register(r'solutions', api_views.SolutionViewSet)
router.register(r'patterns', api_views.PatternViewSet)
router.register(r'users', api_views.UserViewSet)

app_name = 'core'

urlpatterns = [
    path('api/', include(router.urls)),
]