# -*- coding: utf-8 -*-
"""
Real-time Fish Recognition System
Based on research_fishial.py
"""

import os
import sys
import copy
import cv2
import numpy as np
import time
import threading
import queue
from collections import deque
import logging
import torch
import json

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Import model inference classes
from models.classification.inference import EmbeddingClassifier
from models.detection.inference import YOLOInference
from models.segmentation.inference import Inference
from models.face_detector.inference import YOLOInference as FaceInference


class RealTimeFishRecognition:
    def __init__(self, model_dirs=None, camera_id=0, display_fps=True):
        """
        Initialize real-time fish recognition system
        
        Args:
            model_dirs: Dictionary of model directories
            camera_id: Camera ID for video capture (0 for default webcam)
            display_fps: Whether to display FPS counter
        """
        self.camera_id = camera_id
        self.display_fps = display_fps
        self.running = False
        
        # Model directories
        if model_dirs is None:
            self.model_dirs = {
                'classification': "models/classification",
                'segmentation': "models/segmentation", 
                'detection': "models/detection",
                'face': "models/face_detector"
            }
        else:
            self.model_dirs = model_dirs
            
        # FPS tracking
        self.fps_queue = deque(maxlen=30)
        self.frame_count = 0
        self.last_time = time.time()
        
        # Performance settings
        self.skip_frames = 2  # Process every 3rd frame for better performance
        self.frame_counter = 0
        
        # Initialize models
        self._initialize_models()
        
        # Initialize camera
        self._initialize_camera()
        
        logging.info("Real-time fish recognition system initialized")
    
    def _initialize_models(self):
        """Initialize all AI models"""
        try:
            logging.info("Loading AI models...")
            
            # Classification model
            self.classifier = EmbeddingClassifier(
                os.path.join(self.model_dirs['classification'], 'model.ts'),
                os.path.join(self.model_dirs['classification'], 'database.pt')
            )
            
            # Segmentation model
            self.segmentator = Inference(
                model_path=os.path.join(self.model_dirs['segmentation'], 'model.ts'),
                image_size=416
            )
            
            # Fish detection model
            self.detector = YOLOInference(
                os.path.join(self.model_dirs['detection'], 'model.ts'),
                imsz=(640, 640),
                conf_threshold=0.7,  # Increased for better real-time performance
                nms_threshold=0.3,
                yolo_ver='v10'
            )
            
            # Face detection model
            self.face_detector = FaceInference(
                os.path.join(self.model_dirs['face'], 'model.ts'),
                imsz=(640, 640),
                conf_threshold=0.69,
                nms_threshold=0.5,
                yolo_ver='v8'
            )
            
            logging.info("All models loaded successfully")
            
        except Exception as e:
            logging.error(f"Error loading models: {e}")
            raise
    
    def _initialize_camera(self):
        """Initialize camera capture"""
        try:
            self.cap = cv2.VideoCapture(self.camera_id)
            
            # Set camera properties for better performance
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            if not self.cap.isOpened():
                raise RuntimeError(f"Cannot open camera {self.camera_id}")
                
            logging.info(f"Camera {self.camera_id} initialized successfully")
            
        except Exception as e:
            logging.error(f"Error initializing camera: {e}")
            raise
    
    def _process_frame(self, frame):
        """
        Process a single frame for fish detection and classification
        
        Args:
            frame: BGR image frame from camera
            
        Returns:
            processed_frame: Frame with annotations
            fish_results: List of detection results
        """
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        processed_frame = frame.copy()
        fish_results = []
        
        try:
            # Face detection (optional, can be disabled for better performance)
            # face_boxes = self.face_detector.predict(frame_rgb)[0]
            # for box in face_boxes:
            #     box.draw_label(frame_rgb, "Face")
            #     box.draw_box(frame_rgb)
            
            # Fish detection
            detection_start = time.time()
            boxes = self.detector.predict(frame_rgb)[0]
            detection_time = time.time() - detection_start
            
            for i, box in enumerate(boxes):
                try:
                    # Get cropped fish image
                    cropped_fish_bgr = box.get_mask_BGR()
                    cropped_fish_rgb = box.get_mask_RGB()
                    
                    if cropped_fish_bgr is None or cropped_fish_bgr.size == 0:
                        continue
                    
                    # Segmentation (optional for real-time, can be disabled)
                    seg_start = time.time()
                    segmented_polygons = self.segmentator.predict(cropped_fish_bgr)[0]
                    seg_time = time.time() - seg_start
                    
                    # Move polygons to correct position and draw
                    segmented_polygons.move_to(box.x1, box.y1)
                    segmented_polygons.draw_polygon(frame_rgb)
                    
                    # Classification
                    class_start = time.time()
                    classification_result = self.classifier.batch_inference([cropped_fish_bgr])[0]
                    class_time = time.time() - class_start
                    
                    # Prepare result
                    if classification_result:
                        fish_name = classification_result[0]['name']
                        accuracy = classification_result[0]['accuracy']
                        label = f"{fish_name} | {accuracy:.2%}"
                        
                        fish_results.append({
                            'name': fish_name,
                            'accuracy': accuracy,
                            'bbox': [box.x1, box.y1, box.x2, box.y2],
                            'detection_time': detection_time,
                            'segmentation_time': seg_time,
                            'classification_time': class_time
                        })
                    else:
                        label = "Unknown Fish"
                        fish_results.append({
                            'name': 'Unknown',
                            'accuracy': 0.0,
                            'bbox': [box.x1, box.y1, box.x2, box.y2],
                            'detection_time': detection_time,
                            'segmentation_time': seg_time,
                            'classification_time': class_time
                        })
                    
                    # Draw bounding box and label on processed frame
                    box.draw_label(frame_rgb, label)
                    box.draw_box(frame_rgb)
                    
                except Exception as e:
                    logging.warning(f"Error processing fish {i}: {e}")
                    continue
            
            # Convert back to BGR for display
            processed_frame = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
            
        except Exception as e:
            logging.error(f"Error processing frame: {e}")
            processed_frame = frame.copy()
        
        return processed_frame, fish_results
    
    def _calculate_fps(self):
        """Calculate and return current FPS"""
        current_time = time.time()
        self.fps_queue.append(current_time)
        
        if len(self.fps_queue) >= 2:
            fps = len(self.fps_queue) / (self.fps_queue[-1] - self.fps_queue[0])
            return fps
        return 0
    
    def _draw_info_overlay(self, frame, fish_results, fps):
        """Draw information overlay on frame"""
        height, width = frame.shape[:2]
        
        # Draw FPS
        if self.display_fps:
            cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        # Draw fish count
        fish_count = len(fish_results)
        cv2.putText(frame, f"Fish Detected: {fish_count}", (10, 70), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        # Draw instructions
        cv2.putText(frame, "Press 'q' to quit, 's' to save frame", (10, height - 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Draw fish information
        y_offset = 110
        for i, result in enumerate(fish_results[:5]):  # Show max 5 fish
            text = f"{i+1}. {result['name']} ({result['accuracy']:.1%})"
            cv2.putText(frame, text, (10, y_offset), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
            y_offset += 25
    
    def save_frame(self, frame, fish_results):
        """Save current frame with detection results"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        
        # Save image
        img_filename = f"fish_detection_{timestamp}.jpg"
        cv2.imwrite(img_filename, frame)
        
        # Save results
        results_filename = f"fish_results_{timestamp}.json"
        with open(results_filename, 'w') as f:
            json.dump(fish_results, f, indent=2)
        
        logging.info(f"Saved frame: {img_filename} and results: {results_filename}")
    
    def run(self):
        """Run the real-time fish recognition system"""
        self.running = True
        logging.info("Starting real-time fish recognition...")
        
        try:
            while self.running:
                ret, frame = self.cap.read()
                if not ret:
                    logging.error("Failed to read frame from camera")
                    break
                
                self.frame_counter += 1
                
                # Skip frames for better performance
                if self.frame_counter % (self.skip_frames + 1) == 0:
                    # Process frame
                    processed_frame, fish_results = self._process_frame(frame)
                else:
                    processed_frame = frame.copy()
                    fish_results = []
                
                # Calculate FPS
                fps = self._calculate_fps()
                
                # Draw overlay information
                self._draw_info_overlay(processed_frame, fish_results, fps)
                
                # Display frame
                cv2.imshow('Real-time Fish Recognition', processed_frame)
                
                # Handle keyboard input
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('s'):
                    self.save_frame(processed_frame, fish_results)
                
        except KeyboardInterrupt:
            logging.info("Interrupted by user")
        except Exception as e:
            logging.error(f"Error in main loop: {e}")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Cleanup resources"""
        self.running = False
        if hasattr(self, 'cap'):
            self.cap.release()
        cv2.destroyAllWindows()
        logging.info("Cleanup completed")


def main():
    """Main function to run real-time fish recognition"""
    try:
        # Initialize the system
        fish_recognizer = RealTimeFishRecognition(
            camera_id=0,  # Use default webcam
            display_fps=True
        )
        
        # Run the system
        fish_recognizer.run()
        
    except Exception as e:
        logging.error(f"Error in main: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()