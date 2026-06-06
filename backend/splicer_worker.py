import os
import subprocess
import json
import logging

logger = logging.getLogger(__name__)

OUTPUTS_DIR = os.path.join(os.path.dirname(__file__), "outputs")
EDITOR_SCRIPT = os.path.join(os.path.dirname(__file__), "editor.py")

def _prep_clip(clip: dict, video_id: str, fight_id: int, phase_name: str, out_dir: str) -> str:
    start_t = float(clip['start_time'])
    end_t = float(clip['end_time'])
    duration = end_t - start_t
    
    raw_punch_ins = clip.get('visual_punch_in_timestamps', [])
    relative_punch_ins = [float(pt) for pt in raw_punch_ins if 0 <= float(pt) <= duration]
    
    out_file = os.path.join(out_dir, f"{video_id}_fight_{fight_id}_{phase_name}.mp4")
    json_file = os.path.join(out_dir, f"{video_id}_fight_{fight_id}_{phase_name}.json")
    
    story_text = clip.get('story_text', '')
    
    mapped_effects = []
    for eff in clip.get('effects', []):
        eff_copy = eff.copy()
        if 'relative_start_time' in eff_copy:
            eff_copy['start_time'] = eff_copy.pop('relative_start_time')
        mapped_effects.append(eff_copy)
        
    with open(json_file, 'w') as jf:
        json.dump({
            "visual_punch_in_timestamps": relative_punch_ins, 
            "duration": duration,
            "story_text": story_text,
            "effects": mapped_effects
        }, jf)
    
    cmd = [
        "ffmpeg", "-y", 
        "-i", video_path, 
        "-ss", str(start_t),
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
        "-c:a", "aac", "-async", "1",
        out_file
    ]
    
    logger.debug(f"Running ffmpeg cmd: {' '.join(cmd)}")
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    logger.info(f"Successfully spliced clip: {out_file}")
    
    return out_file

def slice_video_into_buckets(video_path: str, segments_json_path: str):
    """
    Reads the _segments.json containing top_fights, splices them, and immediately triggers editor.py
    for each complete FightArc.
    """
    # Make video_path accessible to _prep_clip
    globals()['video_path'] = video_path
    
    logger.info(f"Starting to slice video {video_path} using segments from {segments_json_path}")
    with open(segments_json_path, 'r') as f:
        data = json.load(f)
        
    video_id = os.path.splitext(os.path.basename(video_path))[0]
    
    prop_dir = os.path.join(OUTPUTS_DIR, "Proposition")
    strug_dir = os.path.join(OUTPUTS_DIR, "Struggle")
    res_dir = os.path.join(OUTPUTS_DIR, "Result")
    
    os.makedirs(prop_dir, exist_ok=True)
    os.makedirs(strug_dir, exist_ok=True)
    os.makedirs(res_dir, exist_ok=True)
    
    fights = data.get("top_fights", [])
    
    if not fights:
        logger.warning(f"No fights found in {segments_json_path}.")
        return

    for fight in fights:
        fight_id = fight.get("fight_number", 0)
        logger.info(f"Processing Fight #{fight_id}...")
        
        prop_file = _prep_clip(fight["proposition"], video_id, fight_id, "prop", prop_dir)
        strug_file = _prep_clip(fight["struggle"], video_id, fight_id, "strug", strug_dir)
        res_file = _prep_clip(fight["result"], video_id, fight_id, "res", res_dir)
        
        # Trigger the final render pipeline for this cohesive fight arc
        logger.info(f"Triggering editor.py for Fight #{fight_id}...")
        try:
            import sys
            subprocess.run([sys.executable, EDITOR_SCRIPT, prop_file, strug_file, res_file], check=True)
            logger.info(f"Successfully rendered final short for Fight #{fight_id}!")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to render short for Fight #{fight_id}: {e}")
    
    logger.info(f"Finished processing all fights for {video_path}.")
