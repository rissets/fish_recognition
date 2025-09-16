"""
WebSocket Consumer for Real-time Fish Recognition
Integrates with the RealTimeFishRecognition engine
"""

import json
import asyncio
import base64
import cv2
import numpy as np
import logging
import time
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.exceptions import StopConsumer
from django.conf import settings
import sys
import os

# Add parent directory to path to import our fish recognition module
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

logger = logging.getLogger(__name__)

class FishRecognitionConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time fish recognition"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fish_recognizer = None
        self.is_running = False
        self.camera_task = None
        
    async def connect(self):
        """Accept WebSocket connection"""
        await self.accept()
        logger.info(f"WebSocket connected: {self.channel_name}")
        
        # Send connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'connection',
            'message': 'Connected to Fish Recognition WebSocket',
            'status': 'connected'
        }))
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        logger.info(f"WebSocket disconnected: {self.channel_name}, code: {close_code}")
        await self.stop_recognition()
        
    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'start_recognition':
                await self.start_recognition(data)
            elif message_type == 'stop_recognition':
                await self.stop_recognition()
            elif message_type == 'process_frame':
                await self.process_frame(data)
            elif message_type == 'get_status':
                await self.send_status()
            else:
                await self.send_error(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            await self.send_error("Invalid JSON format")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await self.send_error(f"Error processing message: {str(e)}")
    
    async def start_recognition(self, data):
        """Start the fish recognition system"""
        try:
            if self.is_running:
                await self.send_error("Recognition is already running")
                return
            
            # Initialize fish recognizer
            camera_id = data.get('camera_id', 0)
            await self.initialize_recognizer(camera_id)
            
            if self.fish_recognizer is None:
                await self.send_error("Failed to initialize fish recognizer")
                return
            
            self.is_running = True
            
            # Start camera processing task
            self.camera_task = asyncio.create_task(self.camera_loop())
            
            await self.send(text_data=json.dumps({
                'type': 'recognition_started',
                'message': 'Fish recognition started successfully',
                'camera_id': camera_id
            }))
            
        except Exception as e:
            logger.error(f"Error starting recognition: {e}")
            await self.send_error(f"Failed to start recognition: {str(e)}")
    
    async def stop_recognition(self):
        """Stop the fish recognition system"""
        try:
            self.is_running = False
            
            if self.camera_task:
                self.camera_task.cancel()
                try:
                    await self.camera_task
                except asyncio.CancelledError:
                    pass
                self.camera_task = None
            
            if self.fish_recognizer:
                await asyncio.get_event_loop().run_in_executor(
                    None, self.fish_recognizer.cleanup
                )
                self.fish_recognizer = None
            
            await self.send(text_data=json.dumps({
                'type': 'recognition_stopped',
                'message': 'Fish recognition stopped successfully'
            }))
            
        except Exception as e:
            logger.error(f"Error stopping recognition: {e}")
            await self.send_error(f"Failed to stop recognition: {str(e)}")
    
    async def initialize_recognizer(self, camera_id):
        """Initialize the fish recognition system"""
        try:
            # Import here to avoid import issues
            from realtime_fish_recognition import RealTimeFishRecognition
            
            # Get model directories from settings
            model_dirs = settings.FISH_RECOGNITION_SETTINGS['MODEL_DIRS']
            
            # Create a custom initializer that handles camera properly
            def create_recognizer():
                recognizer = RealTimeFishRecognition.__new__(RealTimeFishRecognition)
                recognizer.camera_id = camera_id
                recognizer.display_fps = False
                recognizer.running = False
                
                # Set up model directories with correct keys for realtime_fish_recognition.py
                recognizer.model_dirs = {
                    'classification': model_dirs['classification'],
                    'segmentation': model_dirs['segmentation'], 
                    'detection': model_dirs['detection'],
                    'face': model_dirs['face_detector']  # Map face_detector to face key
                }
                
                # Initialize FPS tracking
                recognizer.fps_queue = __import__('collections').deque(maxlen=30)
                recognizer.frame_count = 0
                recognizer.last_time = time.time()
                recognizer.skip_frames = 2
                recognizer.frame_counter = 0
                
                # Initialize models
                recognizer._initialize_models()
                
                # Initialize camera if camera_id >= 0
                if camera_id >= 0:
                    recognizer._initialize_camera()
                else:
                    recognizer.cap = None
                
                return recognizer
            
            # Initialize in thread executor to avoid blocking
            self.fish_recognizer = await asyncio.get_event_loop().run_in_executor(
                None, create_recognizer
            )
            
            logger.info("Fish recognizer initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing recognizer: {e}")
            self.fish_recognizer = None
            raise
    
    async def camera_loop(self):
        """Main camera processing loop"""
        try:
            frame_counter = 0
            skip_frames = settings.FISH_RECOGNITION_SETTINGS.get('SKIP_FRAMES', 0)
            max_fps = settings.FISH_RECOGNITION_SETTINGS.get('MAX_FPS', 30)
            frame_delay = 1.0 / max_fps if max_fps > 0 else 0.033  # Target frame delay
            
            while self.is_running:
                start_time = time.time()
                
                # Capture frame in thread executor
                frame_data = await asyncio.get_event_loop().run_in_executor(
                    None, self.capture_frame
                )
                
                if frame_data is None:
                    await asyncio.sleep(frame_delay)
                    continue
                
                frame_counter += 1
                
                # Process frames based on skip setting (0 = process all frames)
                should_process = (skip_frames == 0) or (frame_counter % (skip_frames + 1) == 0)
                
                if should_process:
                    # Process frame in thread executor
                    result = await asyncio.get_event_loop().run_in_executor(
                        None, self.process_frame_sync, frame_data
                    )
                    
                    if result:
                        await self.send_recognition_result(result)
                else:
                    # Send frame without processing for smoother video
                    try:
                        # Resize and encode frame quickly
                        frame_resize = settings.FISH_RECOGNITION_SETTINGS.get('FRAME_RESIZE', (640, 480))
                        frame_quality = settings.FISH_RECOGNITION_SETTINGS.get('FRAME_QUALITY', 70)
                        
                        resized_frame = cv2.resize(frame_data, frame_resize)
                        _, buffer = cv2.imencode('.jpg', resized_frame, [cv2.IMWRITE_JPEG_QUALITY, frame_quality])
                        frame_base64 = base64.b64encode(buffer).decode('utf-8')
                        
                        await self.send_recognition_result({
                            'frame': frame_base64,
                            'fish_results': [],
                            'fps': self.calculate_fps_sync(),
                            'timestamp': time.time(),
                            'processed': False
                        })
                    except Exception as e:
                        logger.warning(f"Error sending unprocessed frame: {e}")
                
                # Control loop speed for consistent FPS
                elapsed = time.time() - start_time
                sleep_time = max(0, frame_delay - elapsed)
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                
        except asyncio.CancelledError:
            logger.info("Camera loop cancelled")
        except Exception as e:
            logger.error(f"Error in camera loop: {e}")
            await self.send_error(f"Camera error: {str(e)}")
    
    def get_optimal_frame_size(self, original_width, original_height):
        """Calculate optimal frame size while preserving aspect ratio"""
        max_width = settings.FISH_RECOGNITION_SETTINGS.get('MAX_FRAME_WIDTH', 1280)
        max_height = settings.FISH_RECOGNITION_SETTINGS.get('MAX_FRAME_HEIGHT', 720)
        
        # Calculate aspect ratio
        aspect_ratio = original_width / original_height
        
        # Calculate optimal size while preserving aspect ratio
        if original_width <= max_width and original_height <= max_height:
            # Original size is within limits, keep it
            return original_width, original_height
        
        # Need to scale down while preserving aspect ratio
        if original_width / max_width > original_height / max_height:
            # Width is the limiting factor
            new_width = max_width
            new_height = int(max_width / aspect_ratio)
        else:
            # Height is the limiting factor
            new_height = max_height
            new_width = int(max_height * aspect_ratio)
        
        # Ensure dimensions are even (required for some video codecs)
        new_width = new_width if new_width % 2 == 0 else new_width - 1
        new_height = new_height if new_height % 2 == 0 else new_height - 1
        
        return new_width, new_height
    
    def capture_frame(self):
        """Capture frame from camera (runs in thread executor)"""
        try:
            if not self.fish_recognizer or not self.fish_recognizer.cap:
                return None
            
            ret, frame = self.fish_recognizer.cap.read()
            if not ret:
                return None
            
            return frame
            
        except Exception as e:
            logger.error(f"Error capturing frame: {e}")
            return None
    
    def calculate_fps_sync(self):
        """Calculate FPS synchronously"""
        try:
            if self.fish_recognizer:
                return self.fish_recognizer._calculate_fps()
            return 0
        except:
            return 0
    
    def process_frame_sync(self, frame):
        """Process frame synchronously (runs in thread executor)"""
        try:
            if not self.fish_recognizer:
                return None
            
            original_height, original_width = frame.shape[:2]
            preserve_aspect = settings.FISH_RECOGNITION_SETTINGS.get('PRESERVE_ASPECT_RATIO', True)
            
            # Process frame with original size or optimally resized
            processing_frame = frame.copy()
            
            if preserve_aspect:
                # Get optimal size while preserving aspect ratio
                optimal_width, optimal_height = self.get_optimal_frame_size(original_width, original_height)
                
                # Only resize if necessary (for performance)
                if optimal_width != original_width or optimal_height != original_height:
                    processing_frame = cv2.resize(frame, (optimal_width, optimal_height), interpolation=cv2.INTER_AREA)
            
            # Process frame using the fish recognizer
            processed_frame, fish_results = self.fish_recognizer._process_frame(processing_frame)
            
            # Calculate FPS
            fps = self.fish_recognizer._calculate_fps()
            
            # Encode frame with optimized quality, preserve original size for display
            frame_quality = settings.FISH_RECOGNITION_SETTINGS.get('FRAME_QUALITY', 85)
            
            # Use processed frame for encoding (it contains the detection annotations)
            _, buffer = cv2.imencode('.jpg', processed_frame, [cv2.IMWRITE_JPEG_QUALITY, frame_quality])
            frame_base64 = base64.b64encode(buffer).decode('utf-8')
            
            return {
                'frame': frame_base64,
                'fish_results': fish_results,
                'fps': fps,
                'timestamp': time.time(),
                'processed': True,
                'frame_size': f"{processed_frame.shape[1]}x{processed_frame.shape[0]}"
            }
            
        except Exception as e:
            logger.error(f"Error processing frame: {e}")
            return None
    
    async def process_frame(self, data):
        """Process a single frame sent from client"""
        try:
            # Decode base64 frame
            frame_data = data.get('frame')
            if not frame_data:
                await self.send_error("No frame data provided")
                return
            
            # Decode frame
            frame_bytes = base64.b64decode(frame_data)
            nparr = np.frombuffer(frame_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is None:
                await self.send_error("Invalid frame data")
                return
            
            # Process frame
            result = await asyncio.get_event_loop().run_in_executor(
                None, self.process_frame_sync, frame
            )
            
            if result:
                await self.send_recognition_result(result)
            else:
                await self.send_error("Failed to process frame")
                
        except Exception as e:
            logger.error(f"Error processing uploaded frame: {e}")
            await self.send_error(f"Frame processing error: {str(e)}")
    
    async def send_recognition_result(self, result):
        """Send recognition result to client"""
        await self.send(text_data=json.dumps({
            'type': 'recognition_result',
            'data': result
        }))
    
    async def send_status(self):
        """Send current system status"""
        status = {
            'type': 'status',
            'is_running': self.is_running,
            'recognizer_initialized': self.fish_recognizer is not None,
            'camera_connected': self.fish_recognizer and self.fish_recognizer.cap and self.fish_recognizer.cap.isOpened() if self.fish_recognizer else False
        }
        await self.send(text_data=json.dumps(status))
    
    async def send_error(self, message):
        """Send error message to client"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message
        }))
        logger.error(f"Sent error to client: {message}")


class ImageUploadConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for image upload processing"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fish_recognizer = None
    
    async def connect(self):
        """Accept WebSocket connection"""
        await self.accept()
        logger.info(f"Image upload WebSocket connected: {self.channel_name}")
        
        # Initialize recognizer for image processing
        await self.initialize_recognizer()
        
        await self.send(text_data=json.dumps({
            'type': 'connection',
            'message': 'Connected to Image Upload WebSocket',
            'status': 'connected'
        }))
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        logger.info(f"Image upload WebSocket disconnected: {self.channel_name}")
        if self.fish_recognizer:
            await asyncio.get_event_loop().run_in_executor(
                None, self.fish_recognizer.cleanup
            )
    
    async def receive(self, text_data):
        """Handle incoming messages"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'process_image':
                await self.process_image(data)
            else:
                await self.send_error(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            await self.send_error("Invalid JSON format")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await self.send_error(f"Error processing message: {str(e)}")
    
    async def initialize_recognizer(self):
        """Initialize fish recognizer for image processing"""
        try:
            from realtime_fish_recognition import RealTimeFishRecognition
            
            model_dirs = settings.FISH_RECOGNITION_SETTINGS['MODEL_DIRS']
            
            # Create a custom initializer for image processing only
            def create_image_recognizer():
                recognizer = RealTimeFishRecognition.__new__(RealTimeFishRecognition)
                recognizer.camera_id = -1  # No camera
                recognizer.display_fps = False
                recognizer.running = False
                
                # Set up model directories with correct keys for realtime_fish_recognition.py
                recognizer.model_dirs = {
                    'classification': model_dirs['classification'],
                    'segmentation': model_dirs['segmentation'], 
                    'detection': model_dirs['detection'],
                    'face': model_dirs['face_detector']  # Map face_detector to face key
                }
                
                # Initialize FPS tracking (though not used for images)
                recognizer.fps_queue = __import__('collections').deque(maxlen=30)
                recognizer.frame_count = 0
                recognizer.last_time = time.time()
                recognizer.skip_frames = 2
                recognizer.frame_counter = 0
                
                # Initialize models only (no camera)
                recognizer._initialize_models()
                recognizer.cap = None  # Explicitly set to None
                
                return recognizer
            
            # Initialize without camera for image processing
            self.fish_recognizer = await asyncio.get_event_loop().run_in_executor(
                None, create_image_recognizer
            )
            
            logger.info("Image processing recognizer initialized")
            
        except Exception as e:
            logger.error(f"Error initializing image recognizer: {e}")
            self.fish_recognizer = None
    
    async def process_image(self, data):
        """Process uploaded image"""
        try:
            if not self.fish_recognizer:
                await self.send_error("Recognizer not initialized")
                return
            
            # Decode base64 image
            image_data = data.get('image')
            if not image_data:
                await self.send_error("No image data provided")
                return
            
            # Remove data URL prefix if present
            if image_data.startswith('data:image'):
                image_data = image_data.split(',')[1]
            
            # Decode image
            image_bytes = base64.b64decode(image_data)
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if image is None:
                await self.send_error("Invalid image data")
                return
            
            # Process image
            result = await asyncio.get_event_loop().run_in_executor(
                None, self.process_image_sync, image
            )
            
            if result:
                await self.send(text_data=json.dumps({
                    'type': 'image_result',
                    'data': result
                }))
            else:
                await self.send_error("Failed to process image")
                
        except Exception as e:
            logger.error(f"Error processing image: {e}")
            await self.send_error(f"Image processing error: {str(e)}")
    
    def process_image_sync(self, image):
        """Process image synchronously"""
        try:
            # Process image using fish recognizer
            processed_image, fish_results = self.fish_recognizer._process_frame(image)
            
            # Encode processed image
            _, buffer = cv2.imencode('.jpg', processed_image, [cv2.IMWRITE_JPEG_QUALITY, 90])
            processed_base64 = base64.b64encode(buffer).decode('utf-8')
            
            return {
                'processed_image': processed_base64,
                'fish_results': fish_results,
                'fish_count': len(fish_results)
            }
            
        except Exception as e:
            logger.error(f"Error in image processing: {e}")
            return None
    
    async def send_error(self, message):
        """Send error message to client"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message
        }))
        logger.error(f"Sent error to image client: {message}")