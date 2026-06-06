import json
import os
import subprocess
import cv2
import ffmpeg
import logging
import json
import whisperx
from hyperframe import generate_crop_polynomial
from effects.registry import create_effect

logger = logging.getLogger(__name__)

def _parse_time(time_str):
    # Converts MM:SS to seconds
    parts = time_str.split(':')
    return int(parts[0]) * 60 + int(parts[1])

def generate_ass_subtitles(word_segments, output_file="captions.ass"):
    """
    Generates an Advanced SubStation Alpha (.ass) file for dynamic word-by-word captions.
    Style: Bright yellow font, heavy black stroke, center-middle alignment.
    """
    logger.info(f"Generating ASS subtitles to {output_file} with {len(word_segments)} words.")
    ass_header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Pop,Arial,80,&H0000FFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,6,2,5,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    
    def format_time(seconds):
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = seconds % 60
        return f"{h}:{m:02d}:{s:05.2f}"

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(ass_header)
        for seg in word_segments:
            if 'word' in seg and 'start' in seg and 'end' in seg:
                start_t = format_time(seg['start'])
                end_t = format_time(seg['end'])
                word = seg['word'].strip().upper()
                f.write(f"Dialogue: 0,{start_t},{end_t},Pop,,0,0,0,,{word}\n")

def get_average_salient_x(video_path, target_crop_width):
    """
    Analyzes the video to find the average X coordinate of salient motion.
    Uses basic frame differencing.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return 0

    ret, prev_frame = cap.read()
    if not ret:
        return 0

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
    prev_gray = cv2.GaussianBlur(prev_gray, (21, 21), 0)

    motion_x_centers = []

    # Sample every Nth frame for speed
    frame_count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        frame_count += 1
        if frame_count % 5 != 0:
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        # Compute absolute difference
        diff = cv2.absdiff(prev_gray, gray)
        thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)

        contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            # Find largest contour (most motion)
            c = max(contours, key=cv2.contourArea)
            if cv2.contourArea(c) > 500:
                (x, y, w, h) = cv2.boundingRect(c)
                center_x = x + w / 2
                motion_x_centers.append(center_x)

        prev_gray = gray

    cap.release()

    if not motion_x_centers:
        return (width - target_crop_width) // 2

    # Calculate average X
    avg_x = sum(motion_x_centers) / len(motion_x_centers)
    
    # Ensure crop boundaries are valid
    crop_x = int(avg_x - (target_crop_width / 2))
    crop_x = max(0, min(crop_x, width - target_crop_width))
    return crop_x

def render_hyper_short(video_path, retention_timeline_data, output_path="final_viral_short.mp4"):
    """
    Executes the programmatic pipeline: Splice -> Hyperframe -> The Pop.
    """
    if isinstance(retention_timeline_data, str):
        with open(retention_timeline_data, 'r') as f:
            data = json.load(f)
    else:
        data = retention_timeline_data
        
    phases = data.get('phases', [])
    if len(phases) != 3:
        raise ValueError("JSON must contain exactly 3 phases.")

    temp_spliced = "/tmp/temp_spliced.mp4"
    ass_file = "/tmp/captions.ass"
    final_output = output_path

    # --- PHASE 1: SPLICE ---
    print("Phase 1: Splicing segments...")
    inputs = []
    for phase in phases:
        start_t = _parse_time(phase['start_time'])
        end_t = _parse_time(phase['end_time'])
        # Extract subclip
        in_vid = ffmpeg.input(video_path, ss=start_t, t=(end_t - start_t))
        inputs.append(in_vid.video)
        inputs.append(in_vid.audio)
    
    # Concat all segments
    joined = ffmpeg.concat(*inputs, v=1, a=1).node
    out = ffmpeg.output(joined[0], joined[1], temp_spliced, vcodec='libx264', acodec='aac', strict='experimental')
    out.overwrite_output().run(quiet=True)

    # --- PHASE 2: HYPERFRAME (Action Tracking) ---
    print("Phase 2: Hyperframe action tracking...")
    # Get source dimensions
    probe = ffmpeg.probe(temp_spliced)
    video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
    orig_w = int(video_stream['width'])
    orig_h = int(video_stream['height'])

    # 9:16 aspect ratio
    crop_w = int(orig_h * (9 / 16))
    crop_h = orig_h

    # OpenCV to find optimal crop X
    crop_x = get_average_salient_x(temp_spliced, crop_w)
    print(f"Optimal static crop X: {crop_x}")

    # --- PHASE 3: THE POP (Dynamic Captions) ---
    print("Phase 3: The Pop (WhisperX Captions)...")
    device = "cpu" 
    # Use base model for speed
    model = whisperx.load_model("base", device)
    audio = whisperx.load_audio(temp_spliced)
    result = model.transcribe(audio, batch_size=16)

    # Align whisper output
    model_a, metadata = whisperx.load_align_model(language_code=result["language"], device=device)
    result = whisperx.align(result["segments"], model_a, metadata, audio, device, return_char_alignments=False)

    # Extract word segments
    all_words = []
    for segment in result["segments"]:
        if "words" in segment:
            all_words.extend(segment["words"])

    generate_ass_subtitles(all_words, ass_file)

    # --- FINAL RENDER ---
    print("Rendering final viral short...")
    in_file = ffmpeg.input(temp_spliced)
    
    # Chain filters: crop -> scale -> ass subtitles
    filtered_video = (
        in_file.video
        .crop(x=crop_x, y=0, width=crop_w, height=crop_h)
        .scale(1080, 1920)
        # Using hard-coded string for the vf argument because ffmpeg-python doesn't wrap 'ass' natively
    )
    
    # Construct final ffmpeg command string to include ASS filter properly
    # ffmpeg-python can be tricky with external subtitle files, so we use subprocess
    
    ffmpeg_cmd = [
        'ffmpeg', '-y', 
        '-i', temp_spliced,
        '-vf', f"crop={crop_w}:{crop_h}:{crop_x}:0,scale=1080:1920,ass={ass_file}",
        '-c:v', 'libx264',
        '-c:a', 'copy',
        final_output
    ]
    subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    print(f"Success! Viral short rendered to {final_output}")
    
    # Cleanup temp files
    if os.path.exists(temp_spliced): os.remove(temp_spliced)
def assemble_random_short(prop_clip: str, struggle_clip: str, result_clip: str, output_path: str):
    """
    Assembles a short by concatenating pre-sliced Proposition, Struggle, and Result clips.
    Applies Silent Film text, Suspense filters, and Hyperframe tracking.
    """
    temp_spliced = "/tmp/temp_spliced.mp4"
    font_path = os.path.join(os.path.dirname(__file__), "downloads", "impact.ttf")

    # Load relative punch-in timestamps, durations, and story texts
    global_punch_ins = []
    current_time = 0.0
    texts = ["", "", ""]
    clip_effects = []
    
    clips = [prop_clip, struggle_clip, result_clip]
    
    for idx, clip in enumerate(clips):
        json_path = clip.replace('.mp4', '.json')
        clip_objs = []
        speed_mult = 1.0
        if os.path.exists(json_path):
            with open(json_path, 'r') as f:
                meta = json.load(f)
                punch_ins = meta.get('visual_punch_in_timestamps', [])
                
                raw_effects = meta.get('effects', [])
                for eff in raw_effects:
                    obj = create_effect(eff.get('effect_name'), eff.get('start_time', 0.0), eff.get('duration', 999.0))
                    if obj:
                        clip_objs.append(obj)
                        if hasattr(obj, 'speed_factor'):
                            speed_mult = obj.speed_factor
                        if eff.get('effect_name') == 'zoom_punch':
                            punch_ins.append(eff.get('start_time', 0.0))

                for p in punch_ins:
                    global_punch_ins.append(current_time + (p * speed_mult))
                current_time += (meta.get('duration', 0.0) * speed_mult)
                texts[idx] = meta.get('story_text', '').strip()
        clip_effects.append(clip_objs)

    logger.info(f"Global punch-ins calculated (speed-adjusted): {global_punch_ins}")

    # --- PHASE 1: SPLICE JUST FOR TRACKING ---
    # We still need temp_spliced to calculate the average salient X
    logger.info("Phase 1: Generating tracking proxy...")
    list_file = "/tmp/concat_list.txt"
    with open(list_file, "w") as f:
        for clip in clips:
            f.write(f"file '{clip}'\n")
            
    concat_cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", list_file, "-c", "copy", temp_spliced
    ]
    try:
        subprocess.run(concat_cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Concat failed: {e.stderr.decode()}")
        raise

    # --- PHASE 2: HYPERFRAME (Action Tracking) ---
    logger.info("Phase 2: Hyperframe action tracking...")
    # Calculate crop logic for 9:16 dynamically based on source
    probe = ffmpeg.probe(prop_clip)
    video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
    orig_w = int(video_stream['width'])
    orig_h = int(video_stream['height'])
    fps_fraction = video_stream.get('r_frame_rate', '30/1')
    
    crop_w = int(orig_h * (9 / 16))
    crop_h = orig_h
    
    # Run OpenCV Hyperframe tracking! (Static average to prevent jittery panning)
    crop_x_0 = str(get_average_salient_x(prop_clip, target_crop_width=crop_w))
    crop_x_1 = str(get_average_salient_x(struggle_clip, target_crop_width=crop_w))
    crop_x_2 = str(get_average_salient_x(result_clip, target_crop_width=crop_w))


    # --- PHASE 3 & 4: STYLIZATION AND FINAL RENDER ---
    logger.info("Phase 3 & 4: Applying Silent Film Text and Suspense Filters...")
    
    p_text = texts[0].replace("'", "").upper()
    s_text = texts[1].replace("'", "").upper()
    r_text = texts[2].replace("'", "").upper()
    
    base_font = f"fontfile='{font_path}':borderw=4:bordercolor=black:shadowcolor=black@0.8:shadowx=8:shadowy=8:fontsize=70:box=1:boxcolor=black@0.6:boxborderw=20:x=(w-text_w)/2:y='if(lt(t,0.3), h*0.6 + (0.3-t)*200, h*0.6)'"
    font_p = f"{base_font}:fontcolor=white"
    font_s = f"{base_font}:fontcolor=red"
    font_r = f"{base_font}:fontcolor=yellow"

    def build_stream(idx: int, v_in: str, a_in: str, crop_x: str, text: str):
        objs = clip_effects[idx]
        
        c_x = f"({crop_x})"
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
                
        if text:
            font_color = "white" if idx == 0 else "red" if idx == 1 else "yellow"
            v_filters.append(f"drawtext={base_font}:fontcolor={font_color}:text='{text}'")
            
        v_out = f"{v_in}" + ",".join(v_filters) + f"[v{idx}]"
        a_out = f"{a_in}" + ",".join(a_filters) + f"[a{idx}]"
        return v_out, a_out

    # --- SPEED RAMPING (Proposition) ---
    prop_probe = ffmpeg.probe(prop_clip)
    prop_duration = float(prop_probe['format']['duration'])
    
    speed_ramp_filters = ""
    v0_in = "[0:v]"
    a0_in = "[0:a]"
    
    if prop_duration > 15.0:
        logger.info(f"Proposition is {prop_duration}s long. Applying algorithmic speed ramp...")
        ramp_v = f"[0:v]trim=0:3,setpts=PTS-STARTPTS[v0_1];" \
                 f"[0:v]trim=3:{prop_duration-3},setpts=0.33*(PTS-STARTPTS)[v0_2];" \
                 f"[0:v]trim={prop_duration-3}:{prop_duration},setpts=PTS-STARTPTS[v0_3];" \
                 f"[v0_1][v0_2][v0_3]concat=n=3:v=1:a=0[v0_ramped];"
        
        ramp_a = f"[0:a]atrim=0:3,asetpts=PTS-STARTPTS[a0_1];" \
                 f"[0:a]atrim=3:{prop_duration-3},atempo=3.0,asetpts=PTS-STARTPTS[a0_2];" \
                 f"[0:a]atrim={prop_duration-3}:{prop_duration},asetpts=PTS-STARTPTS[a0_3];" \
                 f"[a0_1][a0_2][a0_3]concat=n=3:v=0:a=1[a0_ramped];"
        
        speed_ramp_filters = ramp_v + ramp_a
        v0_in = "[v0_ramped]"
        a0_in = "[a0_ramped]"

    # --- FLASH-FORWARD HOOK ---
    def build_hook_stream():
        v_filters = [
            f"trim=duration=1.5",
            f"setpts=PTS-STARTPTS",
            f"crop={crop_w}:{crop_h}:'{crop_x_2}':0",
            f"fps={fps_fraction}",
            f"scale=1080:1920",
            f"chromashift=cbh=-10:crh=10", 
            f"drawtext={base_font}:fontcolor=yellow:text='WAIT FOR IT...'"
        ]
        a_filters = [
            f"atrim=duration=1.5",
            f"asetpts=PTS-STARTPTS"
        ]
        return f"[3:v]" + ",".join(v_filters) + f"[v_hook]", f"[3:a]" + ",".join(a_filters) + f"[a_hook]"

    v_hook, a_hook = build_hook_stream()
    v0, a0 = build_stream(0, v0_in, a0_in, crop_x_0, p_text)
    v1, a1 = build_stream(1, "[1:v]", "[1:a]", crop_x_1, s_text)
    v2, a2 = build_stream(2, "[2:v]", "[2:a]", crop_x_2, r_text)
    
    concat_filter = f"[v_hook][a_hook][v0][a0][v1][a1][v2][a2]concat=n=4:v=1:a=1[cv][ca]"

    zoom_expr = "1+(in_time*0.002)"
    if global_punch_ins:
        conditions = []
        for t in global_punch_ins:
            conditions.append(f"between(in_time,{t},{t+2})")
        cond_str = "+".join(conditions)
        zoom_expr = f"if({cond_str}, 1.15, 1+(in_time*0.002))"
        
    zoom_filter = f"[cv]zoompan=z='{zoom_expr}':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps={fps_fraction}[zv]"

    bgm_path = os.path.join(os.path.dirname(__file__), "downloads", "bgm.mp3")
    sfx_impact_path = os.path.join(os.path.dirname(__file__), "downloads", "sfx", "impact.mp3")
    
    filter_complex = f"{speed_ramp_filters} {v_hook}; {a_hook}; {v0}; {a0}; {v1}; {a1}; {v2}; {a2}; {concat_filter}; {zoom_filter}"

    ffmpeg_cmd = [
        'ffmpeg', '-y', 
        '-i', prop_clip,
        '-i', struggle_clip,
        '-i', result_clip,
        '-i', result_clip
    ]
    
    input_idx = 3
    final_v = "[zv]"
    
    audio_mix_inputs = ["[ca]"]
    amix_weights = "1"
    
    # Process BGM
    if os.path.exists(bgm_path):
        ffmpeg_cmd.extend(['-i', bgm_path])
        audio_mix_inputs.append(f"[{input_idx}:a]")
        amix_weights += " 0.2"
        input_idx += 1
        
    # Process SFX dynamically at punch-in timestamps
    if os.path.exists(sfx_impact_path) and global_punch_ins:
        for i, t in enumerate(global_punch_ins):
            # Delay in milliseconds
            delay_ms = int(t * 1000)
            ffmpeg_cmd.extend(['-i', sfx_impact_path])
            sfx_in = f"[{input_idx}:a]"
            sfx_out = f"[sfx{i}]"
            # Apply adelay
            filter_complex += f"; {sfx_in}adelay={delay_ms}|{delay_ms}{sfx_out}"
            audio_mix_inputs.append(sfx_out)
            amix_weights += " 1.5" # Make SFX loud
            input_idx += 1
            
    if len(audio_mix_inputs) > 1:
        mix_inputs_str = "".join(audio_mix_inputs)
        filter_complex += f"; {mix_inputs_str}amix=inputs={len(audio_mix_inputs)}:duration=first:weights={amix_weights}[fouta]"
        ffmpeg_cmd.extend([
            '-filter_complex', filter_complex,
            '-map', final_v, '-map', '[fouta]'
        ])
    else:
        ffmpeg_cmd.extend([
            '-filter_complex', filter_complex,
            '-map', final_v, '-map', '[ca]'
        ])
        
    ffmpeg_cmd.extend(['-c:v', 'libx264', '-preset', 'fast', '-shortest', output_path])
    
    logger.debug(f"Running ffmpeg final render...")
    
    try:
        subprocess.run(ffmpeg_cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg render failed: {e.stderr.decode()}")
        raise
    
    logger.info(f"Success! Viral short rendered to {output_path}")
    
    if os.path.exists(temp_spliced): os.remove(temp_spliced)
