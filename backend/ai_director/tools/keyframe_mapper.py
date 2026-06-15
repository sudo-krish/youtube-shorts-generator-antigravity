import subprocess
import logging

logger = logging.getLogger(__name__)

def get_previous_iframe(video_path: str, target_time: float) -> float:
    """
    Finds the nearest preceding I-Frame (Keyframe) timestamp for a given target time.
    """
    if target_time <= 0:
        return 0.0
        
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "frame=pkt_pts_time,pict_type",
        "-of", "csv=print_section=0",
        "-read_intervals", f"%{target_time + 1.0}",
        video_path
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split('\n')
        
        best_iframe = 0.0
        for line in lines:
            parts = line.split(',')
            if len(parts) >= 2:
                try:
                    pts = float(parts[0])
                    pict_type = parts[1].strip()
                    if pict_type == 'I' and pts <= target_time:
                        best_iframe = max(best_iframe, pts)
                except ValueError:
                    continue
                    
        return best_iframe
    except Exception as e:
        logger.warning(f"Failed to extract I-frames from {video_path}, falling back to exact cut: {e}")
        return target_time
