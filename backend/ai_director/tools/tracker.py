import os
import cv2
import json
import logging
from ultralytics import YOLO

logger = logging.getLogger(__name__)

# Load a lightweight YOLOv8 nano model for fast inference
_model = None

def get_yolo_model():
    global _model
    if _model is None:
        try:
            _model = YOLO('yolov8n.pt')
        except Exception as e:
            logger.error(f"Failed to load YOLOv8 model: {e}")
            return None
    return _model

def smooth_coordinates(coords, alpha=0.3):
    """Applies Exponential Moving Average (EMA) to smooth out bounding box jitter."""
    if not coords:
        return []
    
    smoothed = []
    current_ema = coords[0]
    for c in coords:
        current_ema = alpha * c + (1 - alpha) * current_ema
        smoothed.append(current_ema)
    return smoothed

def track_subject(video_path: str, fps: int = 1) -> list:
    """
    Extracts frames at a low FPS, runs YOLO to track the primary subject, 
    and returns smoothed coordinates over time.
    """
    logger.info(f"Running AI Object Tracking on {video_path}...")
    model = get_yolo_model()
    if not model:
        return []
        
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.error(f"Cannot open video for tracking: {video_path}")
        return []
        
    video_fps = cap.get(cv2.CAP_PROP_FPS)
    if video_fps <= 0:
        video_fps = 30
        
    width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    default_x = width / 2 if width > 0 else 960.0
    
    frame_interval = max(1, int(video_fps / fps))
    
    raw_focus_x = []
    timestamps = []
    
    frame_count = 0
    current_time = 0.0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        if frame_count % frame_interval == 0:
            current_time = frame_count / video_fps
            timestamps.append(current_time)
            
            # Run YOLO prediction
            results = model.predict(frame, verbose=False, classes=[0]) # class 0 is 'person'
            
            best_x = default_x
            max_area = 0
            
            for r in results:
                boxes = r.boxes
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0]
                    area = (x2 - x1) * (y2 - y1)
                    if area > max_area:
                        max_area = area
                        best_x = float(x1 + (x2 - x1) / 2)
                        
            # If no person detected, hold the previous position, or default to center
            if max_area == 0:
                if raw_focus_x:
                    best_x = raw_focus_x[-1]
                else:
                    best_x = default_x
                    
            raw_focus_x.append(best_x)
            
        frame_count += 1
        
    cap.release()
    
    # Smooth the coordinates to create a "lazy" cinematic camera pan
    smoothed_x = smooth_coordinates(raw_focus_x, alpha=0.15)
    
    tracking_data = []
    for t, sx in zip(timestamps, smoothed_x):
        tracking_data.append({
            "time": round(t, 2),
            "focus_x": round(sx, 1)
        })
        
    return tracking_data
