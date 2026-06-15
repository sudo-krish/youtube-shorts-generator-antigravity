import os
import json
import subprocess
import logging
import ffmpeg

from .capabilities.effects.registry import create_effect
from .capabilities.transformations.hyperframe import generate_crop_polynomial
from .capabilities.audio.mixing import build_audio_mix_filter
from .capabilities.text.overlays import build_drawtext_filter, run_whisperx

logger = logging.getLogger(__name__)

def execute_pipeline(clips_data: dict, output_path: str):
    """
    Executes an N-Phase pipeline with XFADE transitions. Reads the dynamic array of clips,
    generates tracking crops for each, applies temporal/visual effects,
    and stitches them together using complex xfade offsets.
    """
    clips = clips_data.get("clips", [])
    if not clips:
        logger.error("No clips provided for pipeline execution.")
        return

    # Load Blueprints
    clip_blueprints = []
    for clip in clips:
        json_path = clip.replace('.mp4', '.json')
        meta = {}
        if os.path.exists(json_path):
            with open(json_path, 'r') as f:
                meta = json.load(f)
        clip_blueprints.append(meta)

    # Pre-compute durations for exact XFADE offsets
    durations = []
    for clip in clips:
        probe = ffmpeg.probe(clip)
        dur = float(probe['format']['duration'])
        durations.append(dur)

    xfade_duration = 0.5 # Default transition overlap
    
    # Calculate Global Punch-ins and total timeline duration
    global_punch_ins = []
    current_timeline_time = 0.0
    hook_duration = 1.5
    
    for idx, meta in enumerate(clip_blueprints):
        for t in meta.get("visual_punch_in_timestamps", []):
            # Punch-ins are relative to the start of the phase
            global_punch_ins.append(round(hook_duration + current_timeline_time + t, 2))
            
        current_timeline_time += durations[idx]
        if idx < len(clip_blueprints) - 1:
            # Subtract transition overlap for the next phase
            current_timeline_time -= xfade_duration

    logger.info(f"AI Directed Punch-Ins translated to global timeline: {global_punch_ins}")

    # Load Effects
    clip_effects = []
    for meta in clip_blueprints:
        clip_objs = []
        for eff in meta.get('effects', []):
            obj = create_effect(eff.get('effect_name'), eff.get('start_time', 0.0), eff.get('duration', 999.0))
            if obj: clip_objs.append(obj)
        clip_effects.append(clip_objs)

    # Hyperframe Poly Tracking
    logger.info("Applying Hyperframe core transformation to all N phases...")
    crop_x_polynomials = []
    video_stream = next((stream for stream in ffmpeg.probe(clips[0])['streams'] if stream['codec_type'] == 'video'), None)
    orig_h = int(video_stream['height'])
    fps_fraction = video_stream.get('r_frame_rate', '30/1')
    crop_w = int(orig_h * (9 / 16))
    crop_h = orig_h
    
    for clip in clips:
        crop_x_polynomials.append(generate_crop_polynomial(clip, target_w=crop_w))

    # Build Stream Filter Graph
    logger.info("Building dynamic N-Phase FFmpeg complex filter graph with XFADE...")
    
    def build_stream(idx: int, v_in: str, a_in: str, crop_x: str, meta: dict):
        objs = clip_effects[idx]
        c_x = crop_x
        for obj in objs:
            if hasattr(obj, 'get_crop_offset'):
                offset = obj.get_crop_offset()
                if offset: c_x += "+" + offset
                
        v_filters = [f"crop={crop_w}:{crop_h}:'{c_x}':0"]
        a_filters = ["asetpts=PTS-STARTPTS"]
        temporal_v = "setpts=PTS-STARTPTS"
        
        for obj in objs:
            if hasattr(obj, 'get_temporal_video_filter'):
                temporal_v = obj.get_temporal_video_filter()
                a_filters.append(obj.get_temporal_audio_filter())
                break
                
        v_filters.append(temporal_v)
        v_filters.append(f"fps={fps_fraction}")
        v_filters.append("scale=1080:1920")
        
        for obj in objs:
            if hasattr(obj, 'get_video_filter'):
                vf = obj.get_video_filter()
                if vf: v_filters.append(vf)
            if hasattr(obj, 'get_audio_filter'):
                af = obj.get_audio_filter()
                if af: a_filters.append(af)
        
        story_text = meta.get("story_text", "")
        if story_text:
            tf = build_drawtext_filter(story_text, 0, meta.get("duration", 999.0))
            if tf: v_filters.append(tf)
                
        v_out = f"{v_in}" + ",".join(v_filters) + f"[v_processed_{idx}]"
        a_out = f"{a_in}" + ",".join(a_filters) + f"[a_processed_{idx}]"
        return v_out, a_out

    # Hook Filter (uses last clip as the hook base)
    def build_hook_stream(hook_idx: int):
        v_filters = [
            f"trim=duration={hook_duration}", f"setpts=PTS-STARTPTS",
            f"crop={crop_w}:{crop_h}:'{crop_x_polynomials[-1]}':0",
            f"fps={fps_fraction}", f"scale=1080:1920",
            f"chromashift=cbh=-10:crh=10" # Stylized hook look
        ]
        return f"[{hook_idx}:v]" + ",".join(v_filters) + f"[v_hook]", f"[{hook_idx}:a]atrim=duration={hook_duration},asetpts=PTS-STARTPTS[a_hook]"

    hook_idx = len(clips)
    v_hook, a_hook = build_hook_stream(hook_idx)
    
    stream_outputs = []
    filter_commands = [v_hook, a_hook]
    
    for i in range(len(clips)):
        v_in = f"[{i}:v]"
        a_in = f"[{i}:a]"
        
        v_out, a_out = build_stream(i, v_in, a_in, crop_x_polynomials[i], clip_blueprints[i])
        filter_commands.append(v_out)
        filter_commands.append(a_out)

    # Calculate XFADE Cascades
    # 1. Hook transitions into Phase 0
    hook_xfade_offset = hook_duration - xfade_duration
    if hook_xfade_offset < 0: hook_xfade_offset = 0.1
    
    # Assume default transition if none requested
    first_trans = "pixelize"
    
    filter_commands.append(f"[v_hook][v_processed_0]xfade=transition={first_trans}:duration={xfade_duration}:offset={hook_xfade_offset}[xf_v_0]")
    filter_commands.append(f"[a_hook][a_processed_0]acrossfade=d={xfade_duration}[xf_a_0]")
    
    current_offset = hook_xfade_offset + durations[0] - xfade_duration
    
    last_v_out = "[xf_v_0]"
    last_a_out = "[xf_a_0]"
    
    for i in range(1, len(clips)):
        meta = clip_blueprints[i]
        trans_name = meta.get("transition_in", "fade")
        if not trans_name or trans_name.lower() == "none":
            trans_name = "fade"
            
        next_v_out = f"[xf_v_{i}]"
        next_a_out = f"[xf_a_{i}]"
        
        filter_commands.append(f"{last_v_out}[v_processed_{i}]xfade=transition={trans_name}:duration={xfade_duration}:offset={current_offset}{next_v_out}")
        filter_commands.append(f"{last_a_out}[a_processed_{i}]acrossfade=d={xfade_duration}{next_a_out}")
        
        current_offset += (durations[i] - xfade_duration)
        last_v_out = next_v_out
        last_a_out = next_a_out

    # Rename last output to cv / ca for zoom / mix logic
    filter_commands.append(f"{last_v_out}copy[cv]")
    filter_commands.append(f"{last_a_out}acopy[ca]")

    # Zoom Logic
    zoom_expr = "1+(in_time*0.002)"
    if global_punch_ins:
        conditions = [f"between(in_time,{t},{t+2})" for t in global_punch_ins]
        cond_str = "+".join(conditions)
        zoom_expr = f"if({cond_str}, 1.15, 1+(in_time*0.002))"
        
    zoom_filter = f"[cv]zoompan=z='{zoom_expr}':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps={fps_fraction}[zv]"
    filter_commands.append(zoom_filter)

    filter_complex = "; ".join(filter_commands)

    # Audio Mix
    input_idx_for_mix = hook_idx + 1 
    ffmpeg_args, filter_complex, final_audio_map = build_audio_mix_filter(global_punch_ins, filter_complex, input_idx_for_mix)

    cmd = ['ffmpeg', '-y']
    for clip in clips:
        cmd.extend(['-i', clip])
    cmd.extend(['-i', clips[-1]]) # Re-include last clip for the hook
    
    cmd.extend(ffmpeg_args)
    cmd.extend([
        '-filter_complex', filter_complex,
        '-map', '[zv]', '-map', final_audio_map,
        '-c:v', 'libx264', '-preset', 'fast', '-shortest', output_path
    ])
    
    logger.info(f"Executing final dynamic N-Phase XFADE pipeline to {output_path}...")
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        logger.info("Successfully executed XFADE pipeline.")
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg XFADE pipeline failed: {e.stderr.decode()}")
        raise
