import cv2
import numpy as np
from core.file_manager import file_manager
from ..transformer import BaseTransformer

class YoloPlayerTracker(BaseTransformer):
    name = "yolo"

    def __init__(self, model_path=None, **kwargs):
        super().__init__(**kwargs)
        self._model_path = model_path or file_manager.get_absolute_path("model", "yoloe-26s-seg.pt")
        
    def load_model(self):
        from ultralytics import YOLO
        self.logger.info(f"Loading {self.name} from {self._model_path}...")
        self.model = YOLO(self._model_path)
        self.logger.info(f"{self.name} loaded successfully.")
        
    def unload_model(self):
        self.logger.info(f"Unloading {self.name} model...")
        if self.model is not None:
            del self.model
            self.model = None
            
        import torch, gc
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            gc.collect()

    def _process_frame_for_camera(self, frame, frame_height, frame_width):
        results = self.model.predict(
            source=frame,
            conf=0.35,          
            iou=0.45,           
            device=0 if str(self.device) == "cuda" else "cpu",
            half=False,
            verbose=False,
            classes=[0, 1] 
        )

        candidates = []
        for r in results:
            boxes = r.boxes
            if boxes is None or len(boxes) == 0:
                continue
                
            xyxys = boxes.xyxy.cpu().numpy()
            confs = boxes.conf.cpu().numpy()
            cls_ids = boxes.cls.cpu().numpy()

            for xyxy, conf, cls_id in zip(xyxys, confs, cls_ids):
                x1, y1, x2, y2 = xyxy
                w = x2 - x1
                h = y2 - y1
                if w * h < (frame_width * frame_height * 0.005): 
                    continue
                    
                cx = x1 + w / 2.0
                cy = y1 + h / 2.0
                candidates.append({
                    "cx": float(cx),
                    "cy": float(cy),
                    "w": float(w),
                    "h": float(h),
                    "conf": float(conf),
                    "class_id": int(cls_id)
                })
                
        return candidates

    def process(self, payload: dict) -> dict:
        video_path = payload.get("video_path")
        duration = float(payload.get("duration", 0.0))
        step = float(payload.get("step", 3.0))
        
        if not video_path:
            return {"error": "Missing video_path in payload"}
            
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0: fps = 30
        
        frame_width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        frame_height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        total_frames = int(duration * fps)
        
        step_frames = max(1, int(fps / 4))
        matrix = []
        
        import numpy as np
        for t in np.arange(0, duration, step):
            start_frame = int(t * fps)
            end_frame = int((t + step) * fps)
            
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
            aggregated_boxes = []
            
            current_frame = start_frame
            while current_frame < end_frame and current_frame < total_frames:
                ret, frame = cap.read()
                if not ret:
                    break
                    
                candidates = self._process_frame_for_camera(frame, frame_height, frame_width)
                if candidates:
                    best = max(candidates, key=lambda x: x["conf"])
                    aggregated_boxes.append(best)
                    
                current_frame += step_frames
                cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame)
                
            if not aggregated_boxes:
                output = {"action_focal_point": None}
            else:
                avg_cx = sum(b["cx"] for b in aggregated_boxes) / len(aggregated_boxes)
                avg_cy = sum(b["cy"] for b in aggregated_boxes) / len(aggregated_boxes)
                
                output = {
                    "action_focal_point": {
                        "x": avg_cx,
                        "y": avg_cy,
                        "relative_x": avg_cx / frame_width,
                        "relative_y": avg_cy / frame_height
                    }
                }
                
            matrix.append({"t_float": float(t), **output})
            
        cap.release()
        return {"matrix": matrix}