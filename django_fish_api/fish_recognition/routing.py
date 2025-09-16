"""
WebSocket URL routing for fish recognition
"""

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/fish-recognition/$', consumers.FishRecognitionConsumer.as_asgi()),
    re_path(r'ws/image-upload/$', consumers.ImageUploadConsumer.as_asgi()),
]