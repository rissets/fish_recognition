"""
Serializers for Fish Recognition API
"""

from rest_framework import serializers
from .models import FishDetectionSession, FishDetectionResult, ImageUpload, SystemStats


class FishDetectionResultSerializer(serializers.ModelSerializer):
    """Serializer for fish detection results"""
    
    bbox_area = serializers.ReadOnlyField()
    
    class Meta:
        model = FishDetectionResult
        fields = [
            'id', 'timestamp', 'frame_number', 'fish_name', 'accuracy',
            'bbox_x1', 'bbox_y1', 'bbox_x2', 'bbox_y2', 'bbox_area',
            'detection_time', 'segmentation_time', 'classification_time',
            'metadata'
        ]


class FishDetectionSessionSerializer(serializers.ModelSerializer):
    """Serializer for fish detection sessions"""
    
    detections = FishDetectionResultSerializer(many=True, read_only=True)
    detection_count = serializers.SerializerMethodField()
    
    class Meta:
        model = FishDetectionSession
        fields = [
            'id', 'session_id', 'started_at', 'ended_at', 'is_active',
            'camera_id', 'total_frames_processed', 'total_fish_detected',
            'detections', 'detection_count'
        ]
    
    def get_detection_count(self, obj):
        return obj.detections.count()


class FishDetectionSessionListSerializer(serializers.ModelSerializer):
    """Simplified serializer for session list"""
    
    detection_count = serializers.SerializerMethodField()
    duration = serializers.SerializerMethodField()
    
    class Meta:
        model = FishDetectionSession
        fields = [
            'id', 'session_id', 'started_at', 'ended_at', 'is_active',
            'camera_id', 'total_frames_processed', 'total_fish_detected',
            'detection_count', 'duration'
        ]
    
    def get_detection_count(self, obj):
        return obj.detections.count()
    
    def get_duration(self, obj):
        if obj.ended_at and obj.started_at:
            return (obj.ended_at - obj.started_at).total_seconds()
        return None


class ImageUploadSerializer(serializers.ModelSerializer):
    """Serializer for image uploads"""
    
    class Meta:
        model = ImageUpload
        fields = [
            'id', 'image', 'uploaded_at', 'processed', 'processing_time',
            'fish_count', 'results'
        ]
        read_only_fields = ['processed', 'processing_time', 'fish_count', 'results']


class SystemStatsSerializer(serializers.ModelSerializer):
    """Serializer for system statistics"""
    
    class Meta:
        model = SystemStats
        fields = [
            'id', 'timestamp', 'active_sessions', 'total_frames_processed',
            'average_fps', 'average_processing_time', 'memory_usage', 'cpu_usage'
        ]


class ProcessImageSerializer(serializers.Serializer):
    """Serializer for image processing requests"""
    
    image = serializers.ImageField()
    
    def validate_image(self, value):
        # Validate image size (max 10MB)
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("Image size must be less than 10MB")
        
        # Validate image format
        allowed_formats = ['JPEG', 'JPG', 'PNG', 'BMP']
        if value.image.format not in allowed_formats:
            raise serializers.ValidationError(f"Image format must be one of: {', '.join(allowed_formats)}")
        
        return value


class ProcessFrameSerializer(serializers.Serializer):
    """Serializer for frame processing requests"""
    
    frame_data = serializers.CharField(help_text="Base64 encoded image data")
    session_id = serializers.CharField(required=False, help_text="Optional session ID")
    
    def validate_frame_data(self, value):
        import base64
        
        try:
            # Remove data URL prefix if present
            if value.startswith('data:image'):
                value = value.split(',')[1]
            
            # Try to decode base64
            base64.b64decode(value)
            return value
        except Exception:
            raise serializers.ValidationError("Invalid base64 image data")


class WebSocketConnectionSerializer(serializers.Serializer):
    """Serializer for WebSocket connection requests"""
    
    camera_id = serializers.IntegerField(default=0, min_value=0, max_value=10)
    session_id = serializers.CharField(required=False, max_length=100)
    
    def validate_camera_id(self, value):
        # You can add camera availability check here
        return value