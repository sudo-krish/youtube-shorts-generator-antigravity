"""
Legacy tracker shim — all logic lives in app.transformers.yolo_tracker.
This module re-exports the shared utilities so any existing imports keep working.
"""

from app.transformers.yolo_tracker import (  # noqa: F401
    YoloPlayerTracker,
    compute_iou,
    filter_person_detections,
    nms_deduplicate,
    smooth_coordinates,
    YOLO_CONF,
    CUSTOM_CLASSES,
)


def track_subject(video_path: str, fps: int = 1) -> list:
    """Convenience wrapper that instantiates a tracker, loads the model, and runs."""
    tracker = YoloPlayerTracker()
    tracker.load_model()
    try:
        return tracker.track_subject(video_path, fps)
    finally:
        tracker.unload_model()
