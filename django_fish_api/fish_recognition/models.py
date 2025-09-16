"""
Models for Fish Recognition API
"""

from django.db import models
from django.contrib.auth.models import User
import json


class FishDetectionSession(models.Model):
    """Model to store fish detection sessions"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_id = models.CharField(max_length=100, unique=True)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    camera_id = models.IntegerField(default=0)
    total_frames_processed = models.IntegerField(default=0)
    total_fish_detected = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-started_at']
    
    def __str__(self):
        return f"Session {self.session_id} - {self.started_at}"


class FishDetectionResult(models.Model):
    """Model to store individual fish detection results"""
    
    session = models.ForeignKey(FishDetectionSession, on_delete=models.CASCADE, related_name='detections')
    timestamp = models.DateTimeField(auto_now_add=True)
    frame_number = models.IntegerField()
    
    # Fish information
    fish_name = models.CharField(max_length=100)
    accuracy = models.FloatField()
    
    # Bounding box coordinates
    bbox_x1 = models.IntegerField()
    bbox_y1 = models.IntegerField()
    bbox_x2 = models.IntegerField()
    bbox_y2 = models.IntegerField()
    
    # Processing times
    detection_time = models.FloatField(null=True, blank=True)
    segmentation_time = models.FloatField(null=True, blank=True)
    classification_time = models.FloatField(null=True, blank=True)
    
    # Additional metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.fish_name} ({self.accuracy:.2%}) - {self.timestamp}"
    
    @property
    def bbox_area(self):
        """Calculate bounding box area"""
        return (self.bbox_x2 - self.bbox_x1) * (self.bbox_y2 - self.bbox_y1)


class ImageUpload(models.Model):
    """Model to store uploaded images for processing"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    image = models.ImageField(upload_to='uploads/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)
    processing_time = models.FloatField(null=True, blank=True)
    
    # Results
    fish_count = models.IntegerField(default=0)
    results = models.JSONField(default=list, blank=True)
    
    class Meta:
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"Upload {self.id} - {self.uploaded_at}"


class SystemStats(models.Model):
    """Model to store system performance statistics"""
    
    timestamp = models.DateTimeField(auto_now_add=True)
    active_sessions = models.IntegerField(default=0)
    total_frames_processed = models.IntegerField(default=0)
    average_fps = models.FloatField(default=0.0)
    average_processing_time = models.FloatField(default=0.0)
    memory_usage = models.FloatField(default=0.0)  # MB
    cpu_usage = models.FloatField(default=0.0)  # Percentage
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = "System Statistics"
    
    def __str__(self):
        return f"Stats {self.timestamp}"