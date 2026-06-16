import torch
import gc
import cv2
import os
from ultralytics import YOLO
from .base import BaseTransformer

class YoloPlayerTracker(BaseTransformer):
    def __init__(self, model_path: str = None):
        super().__init__()
        self.model = None
        if model_path is None:
            from core.settings import get_asset_path
            model_path = get_asset_path("yolo11m.pt", "model")
        self.model_path = model_path
        
    def load_model(self):
        if self.model is None:
            if not os.path.exists(self.model_path):
                self.logger.warning(f"YOLO model not found at {self.model_path}. Player tracking will be skipped.")
                return
            
            device = "cuda:0" if torch.cuda.is_available() else "cpu"
            self.logger.info(f"YOLO: Loading tracking model {self.model_path} into {device}...")
            # Initialize with Ultralytics
            self.model = YOLO(self.model_path)
            
    def unload_model(self):
        if self.model is not None:
            self.logger.info("YOLO: Unloading model and clearing VRAM cache...")
            del self.model
            self.model = None
            if torch.cuda.is_available():
                gc.collect()
                torch.cuda.empty_cache()

    def process(self, video_path: str, start_time: float, end_time: float) -> list:
        if self.model is None:
            return []
            
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return []
            
        fps = cap.get(cv2.CAP_PROP_FPS)
        start_frame = int(start_time * fps)
        end_frame = int(end_time * fps)
        
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        
        frames = []
        for f in range(start_frame, end_frame):
            ret, frame = cap.read()
            if not ret:
                break
            frames.append(frame)
            
        cap.release()
        
        if not frames:
            return []
            
        # Run inference on the center frame of the 1-second chunk
        mid_idx = len(frames) // 2
        results = self.model(frames[mid_idx], verbose=False)
        
        detections = []
        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                cls_id = int(box.cls[0].item())
                conf = float(box.conf[0].item())
                
                label = r.names[cls_id] if r.names else str(cls_id)
                
                if label in ["person", "player"] and conf > 0.4:
                    center_x = (x1 + x2) / 2
                    center_y = (y1 + y2) / 2
                    width = x2 - x1
                    height = y2 - y1
                    detections.append({
                        "label": label,
                        "x": center_x,
                        "y": center_y,
                        "w": width,
                        "h": height,
                        "confidence": round(conf, 2)
                    })
                    
        # Prioritize highest confidence person
        detections = sorted(detections, key=lambda x: x["confidence"], reverse=True)
        return detections
