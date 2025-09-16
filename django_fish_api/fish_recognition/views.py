"""
Views for Fish Recognition API
"""

import json
import base64
import time
import uuid
import logging
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings
from rest_framework import status, viewsets, permissions
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
import cv2
import numpy as np

from .models import FishDetectionSession, FishDetectionResult, ImageUpload, SystemStats
from .serializers import (
    FishDetectionSessionSerializer, FishDetectionSessionListSerializer,
    FishDetectionResultSerializer, ImageUploadSerializer, SystemStatsSerializer,
    ProcessImageSerializer, ProcessFrameSerializer, WebSocketConnectionSerializer
)

logger = logging.getLogger(__name__)


def index(request):
    """Main page with fish recognition interface"""
    return render(request, 'fish_recognition/index.html')


class FishDetectionSessionViewSet(viewsets.ModelViewSet):
    """ViewSet for managing fish detection sessions"""
    
    queryset = FishDetectionSession.objects.all()
    permission_classes = [permissions.AllowAny]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return FishDetectionSessionListSerializer
        return FishDetectionSessionSerializer
    
    def perform_create(self, serializer):
        # Generate unique session ID
        session_id = str(uuid.uuid4())
        serializer.save(
            session_id=session_id,
            user=self.request.user if self.request.user.is_authenticated else None
        )
    
    @action(detail=True, methods=['post'])
    def end_session(self, request, pk=None):
        """End a detection session"""
        session = self.get_object()
        session.is_active = False
        session.ended_at = timezone.now()
        session.save()
        
        return Response({
            'message': 'Session ended successfully',
            'session_id': session.session_id
        })
    
    @action(detail=False, methods=['get'])
    def active_sessions(self, request):
        """Get all active sessions"""
        sessions = self.queryset.filter(is_active=True)
        serializer = self.get_serializer(sessions, many=True)
        return Response(serializer.data)


class FishDetectionResultViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing fish detection results"""
    
    queryset = FishDetectionResult.objects.all()
    serializer_class = FishDetectionResultSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        session_id = self.request.query_params.get('session_id')
        if session_id:
            queryset = queryset.filter(session__session_id=session_id)
        return queryset
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get detection statistics"""
        session_id = request.query_params.get('session_id')
        queryset = self.get_queryset()
        
        if session_id:
            queryset = queryset.filter(session__session_id=session_id)
        
        stats = {
            'total_detections': queryset.count(),
            'unique_fish_species': queryset.values('fish_name').distinct().count(),
            'average_accuracy': queryset.aggregate(
                avg_accuracy=models.Avg('accuracy')
            )['avg_accuracy'] or 0,
            'fish_species_distribution': list(
                queryset.values('fish_name')
                .annotate(count=models.Count('id'))
                .order_by('-count')
            )
        }
        
        return Response(stats)


class ImageProcessingView(APIView):
    """API view for processing uploaded images"""
    
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """Process uploaded image for fish detection"""
        try:
            serializer = ProcessImageSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            image_file = serializer.validated_data['image']
            
            # Save image upload record
            upload = ImageUpload.objects.create(
                image=image_file,
                user=request.user if request.user.is_authenticated else None
            )
            
            # Process image
            start_time = time.time()
            result = self._process_image(image_file)
            processing_time = time.time() - start_time
            
            # Update upload record
            upload.processed = True
            upload.processing_time = processing_time
            upload.fish_count = len(result['fish_results'])
            upload.results = result['fish_results']
            upload.save()
            
            return Response({
                'upload_id': upload.id,
                'processing_time': processing_time,
                'fish_count': len(result['fish_results']),
                'fish_results': result['fish_results'],
                'processed_image_url': request.build_absolute_uri(upload.image.url) if upload.image else None
            })
            
        except Exception as e:
            logger.error(f"Error processing image: {e}")
            return Response({
                'error': f'Image processing failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _process_image(self, image_file):
        """Process image using fish recognition engine"""
        try:
            # Import here to avoid circular imports
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            from realtime_fish_recognition import RealTimeFishRecognition
            
            # Read image
            image_array = np.frombuffer(image_file.read(), np.uint8)
            image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
            
            if image is None:
                raise ValueError("Could not decode image")
            
            # Initialize recognizer
            model_dirs = settings.FISH_RECOGNITION_SETTINGS['MODEL_DIRS']
            recognizer = RealTimeFishRecognition(
                model_dirs=model_dirs,
                camera_id=-1,  # No camera needed
                display_fps=False
            )
            
            # Process image
            processed_image, fish_results = recognizer._process_frame(image)
            
            # Cleanup
            recognizer.cleanup()
            
            return {
                'fish_results': fish_results,
                'processed_image': processed_image
            }
            
        except Exception as e:
            logger.error(f"Error in image processing: {e}")
            raise


class FrameProcessingView(APIView):
    """API view for processing individual frames"""
    
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """Process a single frame"""
        try:
            serializer = ProcessFrameSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            frame_data = serializer.validated_data['frame_data']
            session_id = serializer.validated_data.get('session_id')
            
            # Decode frame
            if frame_data.startswith('data:image'):
                frame_data = frame_data.split(',')[1]
            
            frame_bytes = base64.b64decode(frame_data)
            nparr = np.frombuffer(frame_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is None:
                return Response({
                    'error': 'Invalid frame data'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Process frame
            start_time = time.time()
            result = self._process_frame(frame)
            processing_time = time.time() - start_time
            
            # Encode processed frame
            _, buffer = cv2.imencode('.jpg', result['processed_frame'], [cv2.IMWRITE_JPEG_QUALITY, 80])
            processed_frame_base64 = base64.b64encode(buffer).decode('utf-8')
            
            return Response({
                'processing_time': processing_time,
                'fish_count': len(result['fish_results']),
                'fish_results': result['fish_results'],
                'processed_frame': processed_frame_base64
            })
            
        except Exception as e:
            logger.error(f"Error processing frame: {e}")
            return Response({
                'error': f'Frame processing failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _process_frame(self, frame):
        """Process frame using fish recognition engine"""
        try:
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            from realtime_fish_recognition import RealTimeFishRecognition
            
            # Initialize recognizer
            model_dirs = settings.FISH_RECOGNITION_SETTINGS['MODEL_DIRS']
            recognizer = RealTimeFishRecognition(
                model_dirs=model_dirs,
                camera_id=-1,
                display_fps=False
            )
            
            # Process frame
            processed_frame, fish_results = recognizer._process_frame(frame)
            
            # Cleanup
            recognizer.cleanup()
            
            return {
                'processed_frame': processed_frame,
                'fish_results': fish_results
            }
            
        except Exception as e:
            logger.error(f"Error processing frame: {e}")
            raise


class SystemStatsView(APIView):
    """API view for system statistics"""
    
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        """Get current system statistics"""
        try:
            import psutil
            
            # Get system metrics
            memory_info = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Get application metrics
            active_sessions = FishDetectionSession.objects.filter(is_active=True).count()
            total_frames = FishDetectionResult.objects.count()
            
            # Create stats record
            stats = SystemStats.objects.create(
                active_sessions=active_sessions,
                total_frames_processed=total_frames,
                memory_usage=memory_info.used / (1024 * 1024),  # MB
                cpu_usage=cpu_percent
            )
            
            serializer = SystemStatsSerializer(stats)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Error getting system stats: {e}")
            return Response({
                'error': f'Failed to get system stats: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def websocket_info(request):
    """Get WebSocket connection information"""
    return Response({
        'websocket_urls': {
            'realtime_recognition': f"ws://{request.get_host()}/ws/fish-recognition/",
            'image_upload': f"ws://{request.get_host()}/ws/image-upload/"
        },
        'supported_messages': {
            'realtime_recognition': [
                'start_recognition',
                'stop_recognition',
                'process_frame',
                'get_status'
            ],
            'image_upload': [
                'process_image'
            ]
        }
    })


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def health_check(request):
    """Health check endpoint"""
    return Response({
        'status': 'healthy',
        'timestamp': time.time(),
        'version': '1.0.0'
    })