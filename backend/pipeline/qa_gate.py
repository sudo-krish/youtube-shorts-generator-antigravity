import os
import subprocess
import logging
import cv2
import numpy as np
import json

logger = logging.getLogger(__name__)


def validate_structure(video_path: str) -> bool:
    """Uses ffprobe to validate the structural integrity of the final file."""
    try:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=codec_type",
            "-of",
            "json",
            video_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)

        streams = [s.get("codec_type") for s in data.get("streams", [])]
        duration = float(data.get("format", {}).get("duration", 0))

        if duration < 1.0:
            logger.error(f"QA Gate Failed: Duration too short ({duration}s)")
            return False

        if "video" not in streams:
            logger.error("QA Gate Failed: Missing video stream")
            return False

        if "audio" not in streams:
            logger.error("QA Gate Failed: Missing audio stream")
            return False

        return True
    except Exception as e:
        logger.error(f"QA Gate Failed: FFprobe exception: {e}")
        return False


def validate_visuals(video_path: str) -> bool:
    """Uses OpenCV to sample keyframes and check for frozen or blank video."""
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error("QA Gate Failed: OpenCV could not open video")
            return False

        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if frame_count < 10:
            logger.error("QA Gate Failed: Too few frames")
            cap.release()
            return False

        # Sample 10 frames evenly across the video
        step = max(1, frame_count // 10)
        frames = []

        for i in range(10):
            cap.set(cv2.CAP_PROP_POS_FRAMES, i * step)
            ret, frame = cap.read()
            if ret:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                frames.append(gray)

        cap.release()

        if len(frames) < 2:
            return False

        # Check for black frames
        avg_brightness = np.mean([np.mean(f) for f in frames])
        if avg_brightness < 5.0:  # Very dark threshold
            logger.error(
                f"QA Gate Failed: Video is completely dark (avg brightness: {avg_brightness:.2f})"
            )
            return False

        # Check for frozen frames (zero variance across time)
        # Compute differences between consecutive sampled frames
        diffs = []
        for i in range(1, len(frames)):
            diff = cv2.absdiff(frames[i], frames[i - 1])
            diffs.append(np.mean(diff))

        avg_diff = np.mean(diffs)
        if avg_diff < 0.5:  # Extremely low variance
            logger.error(
                f"QA Gate Failed: Video appears frozen (avg frame diff: {avg_diff:.2f})"
            )
            return False

        logger.info(
            f"QA Gate Passed Visual Check. Brightness: {avg_brightness:.2f}, Variance: {avg_diff:.2f}"
        )
        return True

    except ImportError:
        logger.warning("OpenCV not installed. Skipping visual variance validation.")
        return True
    except Exception as e:
        logger.error(f"QA Gate Failed: Visual validation exception: {e}")
        return False


def run_qa_gate(video_path: str) -> bool:
    """
    Runs structural and visual validation.
    Returns True if the video passes the quality gate.
    """
    logger.info(f"Running Automated QA Gate on {os.path.basename(video_path)}...")

    if not os.path.exists(video_path):
        logger.error(f"QA Gate Failed: File does not exist {video_path}")
        return False

    if not validate_structure(video_path):
        return False

    if not validate_visuals(video_path):
        return False

    logger.info("QA Gate Validation Successful.")
    return True
