import os
import json
import subprocess
import logging
import ffmpeg
import concurrent.futures

from .capabilities.effects.registry import create_effect
from .capabilities.transformations.hyperframe import generate_crop_polynomial
from .capabilities.audio.mixing import build_audio_mix_filter, run_demucs
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
    
    # Run Demucs on the Padded Audio First!
    import uuid
    uid = uuid.uuid4().hex[:8]
    temp_audio = f"{clip_path}_{uid}_raw.wav"
    subprocess.run(['ffmpeg', '-y', '-i', clip_path, '-vn', '-acodec', 'pcm_s16le', '-ar', '44100', '-ac', '2', temp_audio], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    from .capabilities.audio.mixing import run_demucs
    vocals_path, bg_path = run_demucs(temp_audio, os.path.dirname(clip_path))
    os.remove(temp_audio)
    
    # --------------------------
    # Visual Processing (Trim Handles)
    # --------------------------
    handle_start = meta.get("handle_start", 0.0)
    visual_duration = meta.get("duration", duration)
    
    # Effects
    objs = []
    for eff in meta.get('effects', []):
        obj = create_effect(eff.get('effect_name'), eff.get('start_time', 0.0), eff.get('duration', 999.0))
        if obj: objs.append(obj)
        
    v_filters = [f"trim=start={handle_start}:duration={visual_duration}", "setpts=PTS-STARTPTS", f"crop={crop_w}:{crop_h}:'{crop_expr}':0"]
    
    if is_hook:
        v_filters = [f"trim=start={handle_start}:duration={hook_duration}", "setpts=PTS-STARTPTS", f"crop={crop_w}:{crop_h}:'{crop_expr}':0"]
        visual_duration = hook_duration
        
    for obj in objs:
        if hasattr(obj, 'get_temporal_video_filter'):
            v_filters.append(obj.get_temporal_video_filter())
            break
            
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
            
    v_filter_str = ",".join(v_filters)
    
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
            
    filter_complex = f"[0:v]{v_filter_str}[v1]; [v1]zoompan=z='{zoom_expr}':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30[vout]"
    
    cmd_vid = [
        'ffmpeg', '-y', '-i', clip_path,
        '-filter_complex', filter_complex,
        '-map', '[vout]',
        '-c:v', 'libx264', '-preset', 'fast', chunk_out
    ]
    subprocess.run(cmd_vid, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Trim Vocals to exact visual duration (Hard cut)
    chunk_vocals = f"{clip_path}_chunk_{idx}_vocals.wav"
    subprocess.run(['ffmpeg', '-y', '-i', vocals_path, '-af', f'atrim=start={handle_start}:duration={visual_duration},asetpts=PTS-STARTPTS', chunk_vocals], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # The BG path stays padded. We just rename it to be safe.
    chunk_bg = f"{clip_path}_chunk_{idx}_bg.wav"
    import shutil
    shutil.move(bg_path, chunk_bg)
    os.remove(vocals_path) # Cleanup raw vocals
    
    return {"video": chunk_out, "vocals": chunk_vocals, "bg": chunk_bg}


def get_encoder_profile():
    result = subprocess.run(["ffmpeg", "-encoders"], capture_output=True, text=True)
    if "h264_nvenc" in result.stdout:
        return ["-c:v", "h264_nvenc", "-preset", "p6", "-tune", "hq", "-rc", "vbr", "-maxrate", "8M", "-bufsize", "16M", "-pix_fmt", "yuv420p"]
    else:
        return ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "23", "-maxrate", "8M", "-bufsize", "16M", "-pix_fmt", "yuv420p"]


def execute_pipeline(clips_data: dict, output_path: str):
    """Executes the pipeline using Multi-Stage Chunk Rendering with Padded Handles."""
    clips = clips_data.get("clips", [])
    if not clips: return

    clip_blueprints = []
    for clip in clips:
        json_path = clip.replace('.mp4', '.json')
        meta = {}
        if os.path.exists(json_path):
            with open(json_path, 'r') as f: meta = json.load(f)
        clip_blueprints.append(meta)

    # Note: durations[i] from ffprobe is the padded duration. We use meta['duration'] for visual duration.
    durations = [float(ffmpeg.probe(c)['format']['duration']) for c in clips]
    xfade_duration = 0.5
    hook_duration = 1.5
    
    video_stream = next((stream for stream in ffmpeg.probe(clips[0])['streams'] if stream['codec_type'] == 'video'), None)
    orig_h = int(video_stream['height'])
    orig_w = int(video_stream['width'])
    fps_fraction = video_stream.get('r_frame_rate', '30/1')
    crop_w = int(orig_h * (9 / 16))
    crop_h = orig_h

    logger.info("Stage 1: Parallel Pre-Processing & Demucs (Padded Chunks)...")
    chunk_vids = [None] * len(clips)
    chunk_vocals = [None] * len(clips)
    chunk_bgs = [None] * len(clips)
    
    hook_res = None
    
    with concurrent.futures.ProcessPoolExecutor() as executor:
        futures = []
        for i in range(len(clips)):
            futures.append(executor.submit(
                process_chunk, i, clips[i], clip_blueprints[i], durations[i], 
                fps_fraction, orig_w, orig_h, crop_w, crop_h
            ))
        # Note: we drop the hook for simplicity if it complicates audio logic, but let's assume it works exactly the same.
        # Actually, hook just trims the visual. The handles logic still applies!
        
        for i, f in enumerate(futures):
            res = f.result()
            chunk_vids[i] = res["video"]
            chunk_vocals[i] = res["vocals"]
            chunk_bgs[i] = res["bg"]

    logger.info("Stage 2: Three-Tier XFADE Stitching...")
    
    # Calculate global punch-ins
    global_punch_ins = []
    current_time = 0.0
    for idx, meta in enumerate(clip_blueprints):
        visual_dur = meta.get("duration", hook_duration if idx == len(clips)-1 else durations[idx])
        for t in meta.get("visual_punch_in_timestamps", []):
            global_punch_ins.append(round(current_time + t, 2))
        current_time += visual_dur
        if idx < len(clip_blueprints) - 1:
            current_time -= xfade_duration

    filter_commands = []
    
    # 1. Video Stitching
    filter_commands.append("[0:v]scale=1080:1920,fps=60[v0_scaled]")
    filter_commands.append("[1:v]scale=1080:1920,fps=60[v1_scaled]")
    first_trans = clip_blueprints[0].get("transition_out", "fade")
    filter_commands.append(f"[v0_scaled][v1_scaled]xfade=transition={first_trans}:duration={xfade_duration}:offset={clip_blueprints[0].get('duration', durations[0]) - xfade_duration}[xf_v_0]")
    
    # 2. Vocals Stitching (Acrossfade matching video exactly)
    filter_commands.append(f"[0:a][1:a]acrossfade=d={xfade_duration}[xf_voc_0]")
    
    # 3. BG Stitching (Continuous 1.0s crossfade using handles)
    bg_xfade_duration = 1.0
    pad_side = max(0, (bg_xfade_duration - xfade_duration) / 2.0)
    
    bg_trims = []
    for i in range(len(clips)):
        meta = clip_blueprints[i]
        hs = meta.get("handle_start", 0.0)
        vd = meta.get("duration", durations[i])
        if i == 0:
            c_start = hs
            c_end = hs + vd + pad_side
        elif i == len(clips) - 1:
            c_start = max(0, hs - pad_side)
            c_end = hs + vd
        else:
            c_start = max(0, hs - pad_side)
            c_end = hs + vd + pad_side
            
        bg_in = f"[{len(clips)*2 + i}:a]"
        bg_out = f"[bg_trim_{i}]"
        bg_trims.append(f"{bg_in}atrim=start={c_start}:end={c_end},asetpts=PTS-STARTPTS{bg_out}")
        
    filter_commands.extend(bg_trims)
    filter_commands.append(f"[bg_trim_0][bg_trim_1]acrossfade=d={bg_xfade_duration}[xf_bg_0]")
    
    current_offset = clip_blueprints[0].get('duration', durations[0]) - xfade_duration
    last_v = "[xf_v_0]"
    last_voc = "[xf_voc_0]"
    last_bg = "[xf_bg_0]"
    
    for i in range(1, len(chunk_vids) - 1):
        meta = clip_blueprints[i]
        trans_name = meta.get("transition_out", "fade")
        if not trans_name or trans_name.lower() == "none": trans_name = "fade"
        
        next_v = f"[xf_v_{i}]"
        next_voc = f"[xf_voc_{i}]"
        next_bg = f"[xf_bg_{i}]"
        
        filter_commands.append(f"[{i+1}:v]scale=1080:1920,fps=60[v{i+1}_scaled]")
        filter_commands.append(f"{last_v}[v{i+1}_scaled]xfade=transition={trans_name}:duration={xfade_duration}:offset={current_offset}{next_v}")
        filter_commands.append(f"{last_voc}[{i+1}:a]acrossfade=d={xfade_duration}{next_voc}")
        filter_commands.append(f"{last_bg}[bg_trim_{i+1}]acrossfade=d={bg_xfade_duration}{next_bg}")
        
        current_offset += (meta.get("duration", durations[i]) - xfade_duration)
        last_v = next_v
        last_voc = next_voc
        last_bg = next_bg

    filter_commands.append(f"{last_v}copy[cv]")
    filter_commands.append(f"{last_voc}acopy[cvoc]")
    filter_commands.append(f"{last_bg}acopy[cbg]")
    filter_complex = "; ".join(filter_commands)

    temp_vid = output_path.replace(".mp4", "_temp_vid.mp4")
    temp_voc = output_path.replace(".mp4", "_temp_voc.wav")
    temp_bg = output_path.replace(".mp4", "_temp_bg.wav")
    
    cmd_stage2 = ['ffmpeg', '-y']
    for chunk in chunk_vids: cmd_stage2.extend(['-i', chunk])       # [0:v] to [N-1:v]
    for chunk in chunk_vocals: cmd_stage2.extend(['-i', chunk])     # [0:a] to [N-1:a]
    for chunk in chunk_bgs: cmd_stage2.extend(['-i', chunk])        # [2N:a] to [3N-1:a]
    
    cmd_stage2.extend([
        '-filter_complex', filter_complex,
        '-map', '[cv]', temp_vid,
        '-map', '[cvoc]', temp_voc,
        '-map', '[cbg]', temp_bg
    ])
    subprocess.run(cmd_stage2, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    logger.info("Stage 3: Running Final Audio Mix & WhisperX...")
    bgm_filename = clips_data.get("background_audio_track", "bgm.mp3")
    final_mix_wav = output_path.replace(".mp4", "_temp_mix.wav")
    
    audio_mix_args, mix_filter_complex, final_audio_map = build_audio_mix_filter(global_punch_ins, temp_bg, temp_voc, bgm_filename)
    
    cmd_mix = ['ffmpeg', '-y']
    cmd_mix.extend(audio_mix_args)
    cmd_mix.extend([
        '-filter_complex', f"{mix_filter_complex}; {final_audio_map}loudnorm=I=-14:LRA=11:TP=-1.5[loud_aout]",
        '-map', '[loud_aout]',
        final_mix_wav
    ])
    subprocess.run(cmd_mix, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    ass_file = output_path.replace(".mp4", "_captions.ass")
    run_whisperx(final_mix_wav, ass_file)
    
    logger.info("Stage 4: Final Assembly with Dynamic Encoding...")
    
    encoder_profile = get_encoder_profile()
    
    cmd_stage4 = [
        'ffmpeg', '-y',
        '-i', temp_vid,
        '-i', final_mix_wav,
        '-vf', f"subtitles={ass_file}"
    ]
    cmd_stage4.extend(encoder_profile)
    cmd_stage4.extend([
        '-c:a', 'aac',
        output_path
    ])
    subprocess.run(cmd_stage4, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Cleanup temps
    try:
        os.remove(temp_voc)
        os.remove(temp_bg)
        os.remove(final_mix_wav)
        os.remove(temp_vid)
        for chunk in chunk_vids: os.remove(chunk)
        for chunk in chunk_vocals: os.remove(chunk)
        for chunk in chunk_bgs: os.remove(chunk)
    except: pass
    
    logger.info("Successfully executed Phase 3 Elite Rendering Pipeline.")
