"""
URL configuration for fish_recognition app
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router for ViewSets
router = DefaultRouter()
router.register(r'sessions', views.FishDetectionSessionViewSet)
router.register(r'detections', views.FishDetectionResultViewSet)

app_name = 'fish_recognition'

urlpatterns = [
    # Main interface
    path('', views.index, name='index'),
    
    # API endpoints
    path('api/', include(router.urls)),
    path('api/process-image/', views.ImageProcessingView.as_view(), name='process_image'),
    path('api/process-frame/', views.FrameProcessingView.as_view(), name='process_frame'),
    path('api/stats/', views.SystemStatsView.as_view(), name='system_stats'),
    path('api/websocket-info/', views.websocket_info, name='websocket_info'),
    path('api/health/', views.health_check, name='health_check'),
]