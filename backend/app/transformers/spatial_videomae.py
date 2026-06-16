import numpy as np
import cv2
from .base import BaseTransformer

class SpatialFlowTransformer(BaseTransformer):
    """
    Replaces the heavy VideoMAE ONNX requirement with a lightweight, zero-VRAM
    OpenCV Dense Optical Flow algorithm to detect spatial camera movement 
    (flicks, strafing, stationary) across a micro-clip window.
    """
    def __init__(self):
        super().__init__()
        
    def load_model(self):
        self.logger.info("SpatialFlow: Initializing OpenCV Dense Optical Flow (Zero-VRAM).")
        
    def unload_model(self):
        self.logger.info("SpatialFlow: Releasing flow memory buffers.")
        
    def _extract_gray_frame(self, cap: cv2.VideoCapture, time_sec: float) -> np.ndarray:
        cap.set(cv2.CAP_PROP_POS_MSEC, time_sec * 1000.0)
        ret, frame = cap.read()
        if not ret:
            return None
        # Resize down to 224x224 for fast optical flow
        frame = cv2.resize(frame, (224, 224), interpolation=cv2.INTER_AREA)
        return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    def process(self, video_path: str, start_time: float, end_time: float) -> list:
        # We extract 2 frames spanning a 0.5s window in the middle of the interval
        mid_time = start_time + ((end_time - start_time) / 2.0)
        t1 = max(0, mid_time - 0.25)
        t2 = mid_time + 0.25
        
        cap = cv2.VideoCapture(video_path)
        prev_gray = self._extract_gray_frame(cap, t1)
        next_gray = self._extract_gray_frame(cap, t2)
        cap.release()
        
        if prev_gray is None or next_gray is None:
            return ["stationary"]
            
        # Calculate Dense Optical Flow
        flow = cv2.calcOpticalFlowFarneback(
            prev_gray, next_gray, None, 
            pyr_scale=0.5, levels=3, winsize=15, 
            iterations=3, poly_n=5, poly_sigma=1.2, flags=0
        )
        
        mag, ang = cv2.cartToPolar(flow[..., 0], flow[..., 1], angleInDegrees=True)
        mean_mag = np.mean(mag)
        mean_ang = np.mean(ang)
        
        # Heuristic classification of movement
        tags = []
        if mean_mag < 2.0:
            tags.append("stationary")
        elif mean_mag > 15.0:
            tags.append("rapid_camera_flick")
        else:
            tags.append("smooth_tracking")
            
            # Angle logic: 0 is Right, 90 is Down, 180 is Left, 270 is Up
            if 315 <= mean_ang or mean_ang < 45:
                tags.append("strafing_right")
            elif 135 <= mean_ang < 225:
                tags.append("strafing_left")
            elif 45 <= mean_ang < 135:
                tags.append("panning_down")
            elif 225 <= mean_ang < 315:
                tags.append("panning_up")
                
        return tags
