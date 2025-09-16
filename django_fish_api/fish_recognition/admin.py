"""
Django admin configuration for fish_recognition app
"""

from django.contrib import admin
from .models import FishDetectionSession, FishDetectionResult, ImageUpload, SystemStats


@admin.register(FishDetectionSession)
class FishDetectionSessionAdmin(admin.ModelAdmin):
    list_display = ('session_id', 'started_at', 'ended_at', 'is_active', 'camera_id', 'total_fish_detected')
    list_filter = ('is_active', 'camera_id', 'started_at')
    search_fields = ('session_id',)
    readonly_fields = ('session_id', 'started_at')
    ordering = ('-started_at',)


@admin.register(FishDetectionResult)
class FishDetectionResultAdmin(admin.ModelAdmin):
    list_display = ('fish_name', 'accuracy', 'timestamp', 'session', 'frame_number')
    list_filter = ('fish_name', 'timestamp')
    search_fields = ('fish_name', 'session__session_id')
    readonly_fields = ('timestamp',)
    ordering = ('-timestamp',)


@admin.register(ImageUpload)
class ImageUploadAdmin(admin.ModelAdmin):
    list_display = ('id', 'uploaded_at', 'processed', 'fish_count', 'processing_time')
    list_filter = ('processed', 'uploaded_at')
    readonly_fields = ('uploaded_at', 'processing_time', 'fish_count', 'results')
    ordering = ('-uploaded_at',)


@admin.register(SystemStats)
class SystemStatsAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'active_sessions', 'total_frames_processed', 'average_fps', 'cpu_usage', 'memory_usage')
    list_filter = ('timestamp',)
    readonly_fields = ('timestamp',)
    ordering = ('-timestamp',)