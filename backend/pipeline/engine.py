import os
import json
import subprocess
import logging
import ffmpeg
import concurrent.futures

from .capabilities.effects.registry import create_effect
from .capabilities.transformations.hyperframe import generate_crop_polynomial
from .capabilities.audio.mixing import build_audio_mix_filter
from .capabilities.text.overlays import build_drawtext_filter, run_whisperx

logger = logging.getLogger(__name__)

def process_chunk(idx, clip_path, meta, duration, fps_fraction, orig_w, orig_h, crop_w, crop_h, is_hook=False, hook_duration=1.5):
    """Processes a single clip into a fully cropped, color-graded, and zoomed chunk."""
    chunk_out = f"{clip_path}_chunk_{idx}.mp4"
    if is_hook:
        chunk_out = f"{clip_path}_hook.mp4"
        
    start_focus_x = meta.get("start_focus_x", orig_w / 2)
    end_focus_x = meta.get("end_focus_x", orig_w / 2)
    
    start_val = max(0, min(orig_w - crop_w, int(start_focus_x - (crop_w / 2))))
    end_val = max(0, min(orig_w - crop_w, int(end_focus_x - (crop_w / 2))))
    
    # Cosine crop panning
    crop_expr = f"{start_val}+({end_val}-{start_val})*(0.5-0.5*cos(PI*(t/{duration})))"
    
    # Effects
    objs = []
    for eff in meta.get('effects', []):
        obj = create_effect(eff.get('effect_name'), eff.get('start_time', 0.0), eff.get('duration', 999.0))
        if obj: objs.append(obj)
        
    v_filters = [f"crop={crop_w}:{crop_h}:'{crop_expr}':0"]
    a_filters = ["asetpts=PTS-STARTPTS"]
    temporal_v = "setpts=PTS-STARTPTS"
    
    if is_hook:
        v_filters.insert(0, f"trim=duration={hook_duration}")
        a_filters.insert(0, f"atrim=duration={hook_duration}")
        duration = hook_duration
        
    for obj in objs:
        if hasattr(obj, 'get_temporal_video_filter'):
            temporal_v = obj.get_temporal_video_filter()
            a_filters.append(obj.get_temporal_audio_filter())
            break
            
    v_filters.append(temporal_v)
    v_filters.append(f"fps={fps_fraction}")
    
    # Global grading
    v_filters.append("eq=contrast=1.15:saturation=1.25:gamma=1.05")
    v_filters.append("unsharp=5:5:1.0")
    v_filters.append("scale=1080:1920")
    
    if is_hook:
        v_filters.append("vignette=PI/4")
        v_filters.append("chromashift=cbh=-10:crh=10")
        
    for obj in objs:
        if hasattr(obj, 'get_video_filter'):
            vf = obj.get_video_filter()
            if vf: v_filters.append(vf)
        if hasattr(obj, 'get_audio_filter'):
            af = obj.get_audio_filter()
            if af: a_filters.append(af)
            
    v_filter_str = ",".join(v_filters)
    a_filter_str = ",".join(a_filters)
    
    # Zoompan
    zoom_expr = "1+(in_time*0.001)"
    punch_ins = meta.get("visual_punch_in_timestamps", [])
    if punch_ins:
        zoom_exprs = []
        for t in punch_ins:
            expr = f"if(lt(in_time,{t}), 1.0, if(lt(in_time,{t+0.5}), 1.0+0.15*(0.5-0.5*cos(PI*((in_time-{t})/0.5))), 1.15))"
            zoom_exprs.append(expr)
        if len(zoom_exprs) > 1:
            zoom_expr = f"max({','.join(zoom_exprs)}) + (in_time*0.001)"
        else:
            zoom_expr = f"({zoom_exprs[0]}) + (in_time*0.001)"
            
    # Combine into complex filter
    filter_complex = f"[0:v]{v_filter_str}[v1]; [v1]zoompan=z='{zoom_expr}':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30[vout]; [0:a]{a_filter_str}[aout]"
    
    cmd = [
        'ffmpeg', '-y', '-i', clip_path,
        '-filter_complex', filter_complex,
        '-map', '[vout]', '-map', '[aout]',
        '-c:v', 'libx264', '-preset', 'fast', '-c:a', 'aac', chunk_out
    ]
    
    subprocess.run(cmd, check=True, capture_output=True)
    return chunk_out


def execute_pipeline(clips_data: dict, output_path: str):
    """Executes the pipeline using Multi-Stage Chunk Rendering."""
    clips = clips_data.get("clips", [])
    if not clips: return

    clip_blueprints = []
    for clip in clips:
        json_path = clip.replace('.mp4', '.json')
        meta = {}
        if os.path.exists(json_path):
            with open(json_path, 'r') as f: meta = json.load(f)
        clip_blueprints.append(meta)

    durations = [float(ffmpeg.probe(c)['format']['duration']) for c in clips]
    xfade_duration = 0.5
    hook_duration = 1.5
    
    video_stream = next((stream for stream in ffmpeg.probe(clips[0])['streams'] if stream['codec_type'] == 'video'), None)
    orig_h = int(video_stream['height'])
    orig_w = int(video_stream['width'])
    fps_fraction = video_stream.get('r_frame_rate', '30/1')
    crop_w = int(orig_h * (9 / 16))
    crop_h = orig_h

    logger.info("Stage 1: Parallel Pre-Processing of Chunks...")
    chunk_files = [None] * len(clips)
    hook_file = None
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        for i in range(len(clips)):
            futures.append(executor.submit(
                process_chunk, i, clips[i], clip_blueprints[i], durations[i], 
                fps_fraction, orig_w, orig_h, crop_w, crop_h
            ))
        hook_future = executor.submit(
            process_chunk, len(clips), clips[-1], clip_blueprints[-1], durations[-1], 
            fps_fraction, orig_w, orig_h, crop_w, crop_h, True, hook_duration
        )
        
        for i, f in enumerate(futures):
            chunk_files[i] = f.result()
        hook_file = hook_future.result()

    # Calculate global punch-ins for audio mix SFX
    global_punch_ins = []
    current_time = 0.0
    for idx, meta in enumerate(clip_blueprints):
        for t in meta.get("visual_punch_in_timestamps", []):
            global_punch_ins.append(round(hook_duration + current_time + t, 2))
        current_time += durations[idx]
        if idx < len(clip_blueprints) - 1:
            current_time -= xfade_duration

    logger.info("Stage 2: XFADE Stitching & Audio Mix...")
    filter_commands = []
    
    first_trans = "pixelize"
    hook_xfade_offset = max(0.1, hook_duration - xfade_duration)
    audio_xfade_duration = 1.0
    
    filter_commands.append(f"[0:v][1:v]xfade=transition={first_trans}:duration={xfade_duration}:offset={hook_xfade_offset}[xf_v_0]")
    filter_commands.append(f"[0:a][1:a]acrossfade=d={audio_xfade_duration}[xf_a_0]")
    
    current_offset = hook_xfade_offset + durations[0] - xfade_duration
    last_v = "[xf_v_0]"
    last_a = "[xf_a_0]"
    
    for i in range(1, len(chunk_files)):
        meta = clip_blueprints[i]
        trans_name = meta.get("transition_in", "fade")
        if not trans_name or trans_name.lower() == "none": trans_name = "fade"
        
        next_v = f"[xf_v_{i}]"
        next_a = f"[xf_a_{i}]"
        
        filter_commands.append(f"{last_v}[{i+1}:v]xfade=transition={trans_name}:duration={xfade_duration}:offset={current_offset}{next_v}")
        filter_commands.append(f"{last_a}[{i+1}:a]acrossfade=d={audio_xfade_duration}{next_a}")
        
        current_offset += (durations[i] - xfade_duration)
        last_v = next_v
        last_a = next_a

    filter_commands.append(f"{last_v}copy[cv]")
    filter_commands.append(f"{last_a}acopy[ca]")
    filter_complex = "; ".join(filter_commands)

    # Audio Mix
    input_idx_for_mix = len(chunk_files) + 1
    bgm_filename = clips_data.get("background_audio_track", "bgm.mp3")
    audio_mix_args, audio_filter_complex, final_audio_map = build_audio_mix_filter(global_punch_ins, filter_complex, input_idx_for_mix, bgm_filename)

    temp_wav = output_path.replace(".mp4", "_temp_mix.wav")
    ass_file = output_path.replace(".mp4", "_captions.ass")
    temp_vid = output_path.replace(".mp4", "_temp_vid.mp4")
    
    cmd_stage2 = ['ffmpeg', '-y']
    cmd_stage2.extend(['-i', hook_file])
    for chunk in chunk_files: cmd_stage2.extend(['-i', chunk])
    cmd_stage2.extend(audio_mix_args)
    cmd_stage2.extend([
        '-filter_complex', audio_filter_complex,
        '-map', '[cv]', '-map', final_audio_map,
        '-c:v', 'libx264', '-preset', 'fast', 
        '-c:a', 'pcm_s16le', # Export audio as wav compatible stream alongside video (wait, no. We export wav and mp4 separately or together?)
    ])
    
    # Wait, it's easier to export the video temp AND the audio temp in one go!
    cmd_stage2.extend([
        '-map', '[cv]', temp_vid,
        '-map', final_audio_map, temp_wav
    ])
    subprocess.run(cmd_stage2, check=True, capture_output=True)

    logger.info("Stage 3: Running WhisperX...")
    run_whisperx(temp_wav, ass_file)
    
    logger.info("Stage 4: Final Assembly with ASS Subtitles...")
    cmd_stage4 = [
        'ffmpeg', '-y',
        '-i', temp_vid,
        '-i', temp_wav,
        '-vf', f"subtitles={ass_file}",
        '-c:v', 'libx264', '-preset', 'fast',
        '-c:a', 'aac',
        output_path
    ]
    subprocess.run(cmd_stage4, check=True, capture_output=True)
    
    # Cleanup temps
    try:
        os.remove(temp_wav)
        os.remove(temp_vid)
        os.remove(hook_file)
        for chunk in chunk_files: os.remove(chunk)
    except: pass
    
    logger.info("Successfully executed Phase 1 Chunk Rendering Pipeline.")
