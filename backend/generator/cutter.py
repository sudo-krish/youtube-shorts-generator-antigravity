import os
import subprocess
import json
import logging
from .file_manager import prepare_project_directory
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ai_director.tools.keyframe_mapper import get_previous_iframe

logger = logging.getLogger(__name__)

def _prep_clip(phase: dict, video_path: str, video_id: str, variant_id: str, phase_index: int, out_dir: str) -> str:
    original_start_t = float(phase['start_time'])
    end_t = float(phase['end_time'])
    
    # Snap to previous I-frame to prevent slow decoding and black frames
    start_t = get_previous_iframe(video_path, original_start_t)
    duration = end_t - start_t
    
    phase_id = phase.get('phase_id', f"phase_{phase_index}")
    
    raw_punch_ins = phase.get('visual_punch_in_timestamps', [])
    relative_punch_ins = [float(pt) for pt in raw_punch_ins if 0 <= float(pt) <= duration]
    
    base_name = f"{video_id}_{variant_id}_{phase_index}_{phase_id}"
    out_file = os.path.join(out_dir, f"{base_name}.mp4")
    json_file = os.path.join(out_dir, f"{base_name}.json")
    
    story_text = phase.get('story_text', '')
    start_focus_x = float(phase.get('start_focus_x', 960.0))
    end_focus_x = float(phase.get('end_focus_x', 960.0))
    
    mapped_effects = []
    for eff in phase.get('effects', []):
        eff_copy = eff.copy()
        if 'relative_start_time' in eff_copy:
            eff_copy['start_time'] = eff_copy.pop('relative_start_time')
        mapped_effects.append(eff_copy)
        
    with open(json_file, 'w') as jf:
        json.dump({
            "visual_punch_in_timestamps": relative_punch_ins, 
            "duration": duration,
            "story_text": story_text,
            "start_focus_x": start_focus_x,
            "end_focus_x": end_focus_x,
            "effects": mapped_effects
        }, jf)
    
    cmd = [
        "ffmpeg", "-y", 
        "-ss", str(start_t),
        "-i", video_path, 
        "-t", str(duration),
        "-c", "copy",
        out_file
    ]
    
    logger.debug(f"Running generator ffmpeg cmd: {' '.join(cmd)}")
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    logger.info(f"Successfully generated file clip: {out_file}")
    
    return out_file

def generate_files_from_json(video_path: str, timeline_json: dict) -> list:
    """Reads the AI Blueprint JSON and slices the video into dynamic N-phase clips per variant."""
    video_id = os.path.splitext(os.path.basename(video_path))[0]
    proj_dir = prepare_project_directory(video_id)
    
    shorts = timeline_json.get("shorts", [])
    if not shorts:
        logger.warning("No shorts found in JSON blueprint.")
        return []

    generated_variants = []

    for short in shorts:
        variant_id = short.get("variant_id", "default")
        template_name = short.get("template_name", "Unknown")
        phases = short.get("phases", [])
        
        logger.info(f"Generator cutting Variant: {variant_id} (Template: {template_name}) with {len(phases)} phases...")
        
        clip_paths = []
        for idx, phase in enumerate(phases):
            clip_path = _prep_clip(phase, video_path, video_id, variant_id, idx, proj_dir)
            clip_paths.append(clip_path)
            
        generated_variants.append({
            "variant_id": variant_id,
            "video_id": video_id,
            "template_name": template_name,
            "background_audio_track": short.get("background_audio_track", "bgm.mp3"),
            "clips": clip_paths
        })
        
    return generated_variants
