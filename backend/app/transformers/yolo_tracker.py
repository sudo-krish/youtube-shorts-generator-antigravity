import torch
import gc
import cv2
import os
import logging
import numpy as np
from ultralytics import YOLO
from .base import BaseTransformer

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# Shared Utilities & Math
# ──────────────────────────────────────────────────────────────

def compute_iou(box_a, box_b):
    xa = max(box_a[0], box_b[0])
    ya = max(box_a[1], box_b[1])
    xb = min(box_a[2], box_b[2])
    yb = min(box_a[3], box_b[3])
    inter = max(0, xb - xa) * max(0, yb - ya)
    area_a = (box_a[2] - box_a[0]) * (box_a[3] - box_a[1])
    area_b = (box_b[2] - box_b[0]) * (box_b[3] - box_b[1])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0

def nms_deduplicate(detections: list, iou_thresh: float = 0.45) -> list:
    if not detections:
        return []

    dets = sorted(detections, key=lambda d: d["conf"], reverse=True)
    kept = []

    for d in dets:
        d_box = d["box"] if "box" in d else (
            d["cx"] - d["w"] / 2, d["cy"] - d["h"] / 2,
            d["cx"] + d["w"] / 2, d["cy"] + d["h"] / 2
        )
        is_dup = False
        for k in kept:
            k_box = k["box"] if "box" in k else (
                k["cx"] - k["w"] / 2, k["cy"] - k["h"] / 2,
                k["cx"] + k["w"] / 2, k["cy"] + k["h"] / 2
            )
            if compute_iou(d_box, k_box) > iou_thresh:
                is_dup = True
                break
        if not is_dup:
            kept.append(d)

    return kept

def smooth_coordinates(coords: list) -> list:
    """
    Applies a 1D Kalman Filter to smooth a sequence of X coordinates.
    Tuned for 'Cinematic Camera Panning' (Slow drift, high momentum).
    """
    if not coords:
        return []

    kf = cv2.KalmanFilter(2, 1)
    kf.transitionMatrix = np.array([[1, 1], [0, 1]], np.float32)
    kf.measurementMatrix = np.array([[1, 0]], np.float32)
    kf.processNoiseCov = np.array([[1e-5, 0], [0, 1e-5]], np.float32) 
    kf.measurementNoiseCov = np.array([[1e-1]], np.float32)
    kf.statePost = np.array([[np.float32(coords[0])], [0.0]], np.float32)

    smoothed = []
    for c in coords:
        kf.predict()
        measurement = np.array([[np.float32(c)]])
        corrected = kf.correct(measurement)
        smoothed.append(float(corrected[0][0]))

    return smoothed

def _create_kalman_2d(init_x: float, init_y: float):
    kf = cv2.KalmanFilter(4, 2)
    kf.transitionMatrix = np.array([
        [1, 1, 0, 0],
        [0, 1, 0, 0],
        [0, 0, 1, 1],
        [0, 0, 0, 1],
    ], np.float32)
    kf.measurementMatrix = np.array([[1, 0, 0, 0], [0, 0, 1, 0]], np.float32)
    kf.processNoiseCov = np.eye(4, dtype=np.float32) * 1e-4
    kf.measurementNoiseCov = np.eye(2, dtype=np.float32) * 5e-2
    kf.statePost = np.array([[init_x], [0.0], [init_y], [0.0]], np.float32)
    kf.errorCovPost = np.eye(4, dtype=np.float32) * 1.0
    return kf

# ──────────────────────────────────────────────────────────────
# Main Tracker Class 
# ──────────────────────────────────────────────────────────────

YOLO_CONF = 0.15

# Semantic Suppression: Explicit categories to catch hallucinations
CUSTOM_CLASSES = [
    "standing enemy player character",       # 0: TRACK this
    "first person view hands holding weapon",# 1: IGNORE 
    "minimap radar HUD top left corner",     # 2: IGNORE 
    "game UI text banners and killfeed",     # 3: IGNORE 
    "dead body lying on the ground"          # 4: IGNORE 
]

TRACK_CLASS_ID = 0

class YoloPlayerTracker(BaseTransformer):
    def __init__(self, model_path: str = None):
        super().__init__()
        self.model = None
        if model_path is None:
            from core.settings import get_asset_path
            self.model_path = get_asset_path("yoloe-26s-seg.pt", "model")
        else:
            self.model_path = model_path

    def load_model(self):
        if self.model is None:
            device = "cuda:0" if torch.cuda.is_available() else "cpu"
            self.logger.info(f"YOLOE-26: Loading model for Camera Panning into {device}...")
            self.model = YOLO(self.model_path)
            self.model.set_classes(CUSTOM_CLASSES)

    def unload_model(self):
        if self.model is not None:
            self.logger.info("YOLOE-26: Unloading model and clearing VRAM cache...")
            del self.model
            self.model = None
            if torch.cuda.is_available():
                gc.collect()
                torch.cuda.empty_cache()

    def _process_frame_for_camera(self, frame, f_h: int, f_w: int) -> list:
        # 640/736 resolution required to see distant enemies in 1080p
        results = self.model.predict(
            frame, verbose=False, imgsz=736, conf=YOLO_CONF, max_det=10
        )

        center_x = f_w / 2
        center_y = f_h / 2
        
        valid_candidates = []
        for r in results:
            for box in r.boxes:
                cls_id = int(box.cls[0].item())
                if cls_id != TRACK_CLASS_ID: 
                    continue

                x1, y1, x2, y2 = [float(v) for v in box.xyxy[0]]
                conf = float(box.conf[0].item())

                w = x2 - x1
                h = y2 - y1
                cx = (x1 + x2) / 2
                cy = (y1 + y2) / 2
                area = w * h
                
                aspect = w / max(h, 1)
                rel_cx = cx / max(f_w, 1)
                rel_cy = cy / max(f_h, 1)
                rel_area = area / max((f_w * f_h), 1)

                # --- SPATIAL GUARDRAILS ---
                # 1. Reject impossible aspects (Dead bodies / UI strips / Ghost poles)
                if aspect > 1.3 or aspect < 0.22: continue
                # 2. Reject Minimap Zone
                if rel_cx < 0.25 and rel_cy < 0.35: continue
                # 3. Reject Viewmodel Zone
                if rel_cy > 0.5 and rel_area > 0.05: continue

                # --- CENTER-WEIGHTED ENGAGEMENT SCORING ---
                dist_from_center = np.sqrt((cx - center_x)**2 + (cy - center_y)**2)
                max_dist = np.sqrt(center_x**2 + center_y**2)
                normalized_dist = dist_from_center / max_dist
                
                # Higher score if closer to the player's crosshair
                engagement_score = conf * (1.0 - (normalized_dist * 0.8))

                valid_candidates.append({
                    "box": (x1, y1, x2, y2),
                    "cx": round(cx, 1),
                    "cy": round(cy, 1),
                    "w": round(w, 1),
                    "h": round(h, 1),
                    "area": area,
                    "conf": round(conf, 2),
                    "score": round(engagement_score, 3) 
                })

        valid_candidates.sort(key=lambda d: d["score"], reverse=True)
        return valid_candidates

    def process(self, video_path: str, start_time: float, end_time: float) -> list:
        """
        Returns center-weighted bounding box detections for a single chunk.
        Samples 3 frames (start, mid, end) to catch sudden appearances.
        """
        if self.model is None:
            self.load_model()
        if self.model is None:
            return []

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            self.logger.error(f"Cannot open video chunk: {video_path}")
            return []

        fps = cap.get(cv2.CAP_PROP_FPS)
        start_frame = int(start_time * fps)
        end_frame = int(end_time * fps)

        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

        frames = []
        for _ in range(start_frame, end_frame):
            ret, frame = cap.read()
            if not ret: break
            frames.append(frame)

        cap.release()
        
        if not frames:
            return []

        # Sample 3 frames (start, mid, end) to catch sudden appearances
        sample_indices = sorted({0, len(frames) // 2, max(0, len(frames) - 1)})
        all_candidates = []
        
        for idx in sample_indices:
            frame = frames[idx]
            f_h, f_w = frame.shape[:2]
            candidates = self._process_frame_for_camera(frame, f_h, f_w)
            all_candidates.extend(candidates)

        detections = nms_deduplicate(all_candidates)
        
        output = []
        for d in detections:
            output.append({
                "label": "enemy",
                "x": d["cx"],
                "y": d["cy"],
                "w": d["w"],
                "h": d["h"],
                "confidence": d["conf"],
                "score": d.get("score", 0.0)
            })

        output.sort(key=lambda d: d["score"], reverse=True)
        return output

    def track_subject(self, video_path: str, fps: int = 1) -> list:
        """
        Runs Center-Weighted tracking designed explicitly for cinematic camera panning.
        """
        if self.model is None: self.load_model()
        if self.model is None: return []

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened(): return []

        video_fps = cap.get(cv2.CAP_PROP_FPS)
        if video_fps <= 0: video_fps = 30
        
        frame_w = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        default_x = frame_w / 2 if frame_w > 0 else 960.0
        frame_interval = max(1, int(video_fps / fps))

        raw_focus_x = []
        timestamps = []
        
        tracked_box = None
        kf = None
        frames_lost = 0
        MAX_COAST_FRAMES = 15 
        
        frame_count = 0

        while True:
            ret, frame = cap.read()
            if not ret: break

            if frame_count % frame_interval == 0:
                current_time = frame_count / video_fps
                timestamps.append(current_time)
                
                f_h, f_w = frame.shape[:2]
                candidates = self._process_frame_for_camera(frame, f_h, f_w)
                chosen = None

                if candidates and tracked_box is not None:
                    best_iou = 0.0
                    best_match = None
                    for c in candidates:
                        score = compute_iou(tracked_box, c["box"])
                        if score > best_iou:
                            best_iou = score
                            best_match = c

                    if best_match and best_iou > 0.15:
                        chosen = best_match
                    else:
                        chosen = candidates[0] 
                elif candidates:
                    chosen = candidates[0]

                if chosen:
                    tracked_box = chosen["box"]
                    frames_lost = 0
                    if kf is None:
                        kf = _create_kalman_2d(chosen["cx"], chosen["cy"])
                    else:
                        kf.predict()
                        kf.correct(np.array([[np.float32(chosen["cx"])], [np.float32(chosen["cy"])]]))
                    raw_focus_x.append(chosen["cx"])
                else:
                    frames_lost += 1
                    if kf is not None and frames_lost <= MAX_COAST_FRAMES:
                        predicted = kf.predict()
                        raw_focus_x.append(float(predicted[0][0]))
                    else:
                        raw_focus_x.append(default_x)

                    if frames_lost > MAX_COAST_FRAMES:
                        tracked_box = None
                        kf = None

            frame_count += 1

        cap.release()
        smoothed_x = smooth_coordinates(raw_focus_x)

        return [{"time": round(t, 2), "focus_x": round(sx, 1)} for t, sx in zip(timestamps, smoothed_x)]