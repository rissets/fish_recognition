"""
Apps configuration for fish_recognition
"""

from django.apps import AppConfig


class FishRecognitionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'fish_recognition'
    verbose_name = 'Fish Recognition'
    
    def ready(self):
        """Initialize the app"""
        pass