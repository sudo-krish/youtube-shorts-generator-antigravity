import os
import json
import subprocess
import logging
import ffmpeg
import concurrent.futures
import shutil
import uuid
from core.file_manager import file_manager
from pathlib import Path as PathLib

from .edits.effects.registry import create_effect
from .edits.audio.mixing import build_audio_mix_filter, run_demucs
from .edits.text.overlays import run_whisperx

logger = logging.getLogger(__name__)


def _extract_and_demucs_audio(clip_path: str) -> tuple[str, str]:
    """Extracts raw audio and separates it into vocals and background."""
    uid = uuid.uuid4().hex[:8]
    temp_audio = f"{clip_path}_{uid}_raw.wav"

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            clip_path,
            "-vn",
            "-acodec",
            "pcm_s16le",
            "-ar",
            "44100",
            "-ac",
            "2",
            temp_audio,
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    vocals_path, bg_path = run_demucs(temp_audio, os.path.dirname(clip_path))
    file_manager.delete_file("tmp", PathLib(temp_audio).name)
    return vocals_path, bg_path


def _build_zoompan_expr(meta: dict) -> str:
    """Builds the FFmpeg zoompan expression based on punch-in timestamps."""
    zoom_expr = "1+(in_time*0.001)"
    punch_ins = meta.get("visual_punch_in_timestamps", [])
    if punch_ins:
        zoom_exprs = []
        for t in punch_ins:
            expr = f"if(lt(in_time,{t}), 1.0, if(lt(in_time,{t + 0.5}), 1.0+0.15*(0.5-0.5*cos(PI*((in_time-{t})/0.5))), 1.15))"
            zoom_exprs.append(expr)
            
        final_max = zoom_exprs[0]
        for expr in zoom_exprs[1:]:
            final_max = f"max({final_max}, {expr})"
            
        zoom_expr = f"({final_max}) + (in_time*0.001)"
    return zoom_expr


def _build_visual_filtergraph(
    meta: dict,
    duration: float,
    fps_fraction: str,
    orig_w: int,
    crop_w: int,
    crop_h: int,
    is_hook: bool,
    hook_duration: float,
) -> tuple[str, float]:
    """Constructs the visual filtergraph string and returns it with the final visual duration."""
    focus_keyframes = meta.get("focus_keyframes", [])
    if focus_keyframes:
        from modules.media.editor.edits.transformations.hyperframe import generate_polynomial_from_keyframes
        crop_expr = generate_polynomial_from_keyframes(focus_keyframes, target_w=crop_w, orig_w=orig_w)
    else:
        # Fallback to legacy static cropping
        start_focus_x = meta.get("start_focus_x", orig_w / 2)
        end_focus_x = meta.get("end_focus_x", orig_w / 2)
        half_crop = crop_w / 2
        crop_expr = f"max(0, min({orig_w}-{crop_w}, ({start_focus_x} - {half_crop}) + ({end_focus_x} - {start_focus_x}) * (0.5 - 0.5 * cos(PI * (t / {duration})))))"

    handle_start = meta.get("handle_start", 0.0)
    visual_duration = meta.get("duration", duration)

    objs = []
    for eff in meta.get("effects", []):
        obj = create_effect(
            eff.get("effect_name"),
            eff.get("start_time", 0.0),
            eff.get("duration", 999.0),
        )
        if obj:
            objs.append(obj)

    v_filters = [
        f"trim=start={handle_start}:duration={visual_duration}",
        "setpts=PTS-STARTPTS",
        f"crop={crop_w}:{crop_h}:'{crop_expr}':'(ih-{crop_h})/2'",
    ]

    if is_hook:
        v_filters = [
            f"trim=start={handle_start}:duration={hook_duration}",
            "setpts=PTS-STARTPTS",
            f"crop={crop_w}:{crop_h}:'{crop_expr}':'(ih-{crop_h})/2'",
        ]
        visual_duration = hook_duration

    for obj in objs:
        if hasattr(obj, "get_temporal_video_filter"):
            v_filters.append(obj.get_temporal_video_filter())
            break

    v_filters.append(f"fps={fps_fraction}")

    # Global grading
    v_filters.extend(
        [
            "eq=contrast=1.15:saturation=1.25:gamma=1.05",
            "unsharp=5:5:1.0",
            "scale=1080:1920",
        ]
    )

    if is_hook:
        v_filters.extend(["vignette=PI/4", "chromashift=cbh=-10:crh=10"])

    for obj in objs:
        if hasattr(obj, "get_video_filter"):
            vf = obj.get_video_filter()
            if vf:
                v_filters.append(vf)

    v_filters.append("format=yuv420p,limiter=min=0:max=255")
    v_filter_str = ",".join(v_filters)
    return v_filter_str, visual_duration


def process_chunk(
    idx: int,
    clip_path: str,
    meta: dict,
    duration: float,
    fps_fraction: str,
    orig_w: int,
    orig_h: int,
    crop_w: int,
    crop_h: int,
    is_hook: bool = False,
    hook_duration: float = 1.5,
) -> dict:
    """Processes a single clip into a fully cropped, color-graded, and zoomed chunk."""
    chunk_out = f"{clip_path}_hook.mp4" if is_hook else f"{clip_path}_chunk_{idx}.mp4"

    vocals_path, bg_path = _extract_and_demucs_audio(clip_path)

    v_filter_str, visual_duration = _build_visual_filtergraph(
        meta, duration, fps_fraction, orig_w, crop_w, crop_h, is_hook, hook_duration
    )
    zoom_expr = _build_zoompan_expr(meta)

    filter_complex = f"[0:v]{v_filter_str}[v1]; [v1]zoompan=z='{zoom_expr}':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30[vout]"

    cmd_vid = [
        "ffmpeg",
        "-y",
        "-i",
        clip_path,
        "-filter_complex",
        filter_complex,
        "-map",
        "[vout]",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        chunk_out,
    ]
    subprocess.run(
        cmd_vid, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

    # Trim Vocals to exact visual duration (Hard cut)
    chunk_vocals = f"{clip_path}_chunk_{idx}_vocals.wav"
    handle_start = meta.get("handle_start", 0.0)

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            vocals_path,
            "-af",
            f"atrim=start={handle_start}:duration={visual_duration},asetpts=PTS-STARTPTS",
            chunk_vocals,
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # The BG path stays padded. We just rename it to be safe.
    chunk_bg = f"{clip_path}_chunk_{idx}_bg.wav"
    shutil.move(bg_path, chunk_bg)

    try:
        file_manager.delete_file("tmp", PathLib(vocals_path).name)  # Cleanup raw vocals
    except OSError as e:
        logger.warning(f"Cleanup of vocals failed: {e}")

    return {"video": chunk_out, "vocals": chunk_vocals, "bg": chunk_bg}


def get_encoder_profile() -> list[str]:
    """Determines the best available FFmpeg encoder profile (Hardware vs Software)."""
    result = subprocess.run(["ffmpeg", "-encoders"], capture_output=True, text=True)
    if "h264_nvenc" in result.stdout:
        return [
            "-c:v",
            "h264_nvenc",
            "-preset",
            "p6",
            "-tune",
            "hq",
            "-rc",
            "vbr",
            "-maxrate",
            "8M",
            "-bufsize",
            "16M",
            "-pix_fmt",
            "yuv420p",
        ]
    return [
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-crf",
        "23",
        "-maxrate",
        "8M",
        "-bufsize",
        "16M",
        "-pix_fmt",
        "yuv420p",
    ]


def _process_chunks_parallel(
    clips: list[str],
    clip_blueprints: list[dict],
    durations: list[float],
    fps_fraction: str,
    orig_w: int,
    orig_h: int,
    crop_w: int,
    crop_h: int,
) -> tuple[list[str], list[str], list[str]]:
    """Runs chunk processing in parallel and returns chunk paths."""
    chunk_vids = [None] * len(clips)
    chunk_vocals = [None] * len(clips)
    chunk_bgs = [None] * len(clips)

    with concurrent.futures.ProcessPoolExecutor() as executor:
        futures = []
        for i, clip in enumerate(clips):
            futures.append(
                executor.submit(
                    process_chunk,
                    i,
                    clip,
                    clip_blueprints[i],
                    durations[i],
                    fps_fraction,
                    orig_w,
                    orig_h,
                    crop_w,
                    crop_h,
                )
            )

        for i, f in enumerate(futures):
            res = f.result()
            chunk_vids[i] = res["video"]
            chunk_vocals[i] = res["vocals"]
            chunk_bgs[i] = res["bg"]

    return chunk_vids, chunk_vocals, chunk_bgs


def _stitch_video_and_audio(
    chunk_vids: list[str],
    chunk_vocals: list[str],
    chunk_bgs: list[str],
    clips: list[str],
    clip_blueprints: list[dict],
    durations: list[float],
    output_path: str,
    hook_duration: float,
    xfade_duration: float,
) -> tuple[str, str, str, list[float]]:
    """Stitches chunks together with crossfades and returns temp paths and global punch-ins."""
    global_punch_ins = []
    current_time = 0.0
    for idx, meta in enumerate(clip_blueprints):
        visual_dur = meta.get(
            "duration", hook_duration if idx == len(clips) - 1 else durations[idx]
        )
        for t in meta.get("visual_punch_in_timestamps", []):
            global_punch_ins.append(round(current_time + t, 2))
        current_time += visual_dur
        if idx < len(clip_blueprints) - 1:
            current_time -= xfade_duration

    filter_commands = []

    # 1. Video Stitching
    filter_commands.append("[0:v]scale=1080:1920,fps=60,settb=1/60000[v0_scaled]")
    filter_commands.append("[1:v]scale=1080:1920,fps=60,settb=1/60000[v1_scaled]")
    first_trans = clip_blueprints[0].get("transition_out", "fade")
    filter_commands.append(
        f"[v0_scaled][v1_scaled]xfade=transition={first_trans}:duration={xfade_duration}:offset={clip_blueprints[0].get('duration', durations[0]) - xfade_duration}[xf_v_0]"
    )

    # 2. Vocals Stitching (Acrossfade matching video exactly)
    filter_commands.append(f"[{len(clips)}:a][{len(clips)+1}:a]acrossfade=d={xfade_duration}[xf_voc_0]")

    # 3. BG Stitching (Continuous 1.0s crossfade using handles)
    bg_xfade_duration = 1.0
    pad_side = max(0.0, (bg_xfade_duration - xfade_duration) / 2.0)

    bg_trims = []
    for i in range(len(clips)):
        meta = clip_blueprints[i]
        hs = meta.get("handle_start", 0.0)
        vd = meta.get("duration", durations[i])
        if i == 0:
            c_start = hs
            c_end = hs + vd + pad_side
        elif i == len(clips) - 1:
            c_start = max(0.0, hs - pad_side)
            c_end = hs + vd
        else:
            c_start = max(0.0, hs - pad_side)
            c_end = hs + vd + pad_side

        bg_in = f"[{len(clips) * 2 + i}:a]"
        bg_out = f"[bg_trim_{i}]"
        bg_trims.append(
            f"{bg_in}atrim=start={c_start}:end={c_end},asetpts=PTS-STARTPTS{bg_out}"
        )

    filter_commands.extend(bg_trims)
    filter_commands.append(
        f"[bg_trim_0][bg_trim_1]acrossfade=d={bg_xfade_duration}[xf_bg_0]"
    )

    current_offset = clip_blueprints[0].get("duration", durations[0]) - xfade_duration
    last_v = "[xf_v_0]"
    last_voc = "[xf_voc_0]"
    last_bg = "[xf_bg_0]"

    for i in range(1, len(chunk_vids) - 1):
        meta = clip_blueprints[i]
        trans_name = meta.get("transition_out", "fade")
        if not trans_name or trans_name.lower() == "none":
            trans_name = "fade"

        next_v = f"[xf_v_{i}]"
        next_voc = f"[xf_voc_{i}]"
        next_bg = f"[xf_bg_{i}]"

        filter_commands.append(f"[{i + 1}:v]scale=1080:1920,fps=60,settb=1/60000[v{i + 1}_scaled]")
        filter_commands.append(
            f"{last_v}[v{i + 1}_scaled]xfade=transition={trans_name}:duration={xfade_duration}:offset={current_offset}{next_v}"
        )
        filter_commands.append(
            f"{last_voc}[{len(clips) + i + 1}:a]acrossfade=d={xfade_duration}{next_voc}"
        )
        filter_commands.append(
            f"{last_bg}[bg_trim_{i + 1}]acrossfade=d={bg_xfade_duration}{next_bg}"
        )

        current_offset += meta.get("duration", durations[i]) - xfade_duration
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

    cmd_stage2 = ["ffmpeg", "-y"]
    for chunk in chunk_vids:
        cmd_stage2.extend(["-i", chunk])
    for chunk in chunk_vocals:
        cmd_stage2.extend(["-i", chunk])
    for chunk in chunk_bgs:
        cmd_stage2.extend(["-i", chunk])

    cmd_stage2.extend(
        [
            "-filter_complex",
            filter_complex,
            "-map",
            "[cv]",
            temp_vid,
            "-map",
            "[cvoc]",
            temp_voc,
            "-map",
            "[cbg]",
            temp_bg,
        ]
    )
    subprocess.run(
        cmd_stage2, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

    return temp_vid, temp_voc, temp_bg, global_punch_ins


def _apply_final_mix_and_encode(
    temp_vid: str,
    temp_voc: str,
    temp_bg: str,
    global_punch_ins: list[float],
    bgm_filename: str,
    output_path: str,
):
    """Mixes audio, generates subtitles, and encodes the final artifact."""
    final_mix_wav = output_path.replace(".mp4", "_temp_mix.wav")

    audio_mix_args, mix_filter_complex, final_audio_map = build_audio_mix_filter(
        global_punch_ins, temp_bg, temp_voc, bgm_filename
    )

    cmd_mix = ["ffmpeg", "-y"]
    cmd_mix.extend(audio_mix_args)
    
    prefix = f"{mix_filter_complex}; " if mix_filter_complex else ""
    filter_complex_str = f"{prefix}{final_audio_map}loudnorm=I=-14:LRA=11:TP=-1.5[loud_aout]"
    
    cmd_mix.extend(
        [
            "-filter_complex",
            filter_complex_str,
            "-map",
            "[loud_aout]",
            final_mix_wav,
        ]
    )
    subprocess.run(
        cmd_mix, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

    # Extract raw game audio (un-demucsed) by mixing the bg and voc back together for WhisperX
    raw_game_audio_wav = output_path.replace(".mp4", "_raw_game.wav")
    cmd_raw = [
        "ffmpeg", "-y",
        "-i", temp_bg,
        "-i", temp_voc,
        "-filter_complex", "[0:a][1:a]amix=inputs=2:duration=longest:normalize=0[aout]",
        "-map", "[aout]",
        raw_game_audio_wav
    ]
    subprocess.run(cmd_raw, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    ass_file = output_path.replace(".mp4", "_captions.ass")
    run_whisperx(raw_game_audio_wav, ass_file)
    
    if PathLib(raw_game_audio_wav).exists():
        file_manager.delete_file("tmp", PathLib(raw_game_audio_wav).name)

    logger.info("Stage 4: Final Assembly with Dynamic Encoding...")
    encoder_profile = get_encoder_profile()

    cmd_stage4 = [
        "ffmpeg",
        "-y",
        "-i",
        temp_vid,
        "-i",
        final_mix_wav,
        "-vf",
        f"subtitles={ass_file}",
    ]
    cmd_stage4.extend(encoder_profile)
    cmd_stage4.extend(["-c:a", "aac", output_path])
    subprocess.run(
        cmd_stage4, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

    try:
        file_manager.delete_file("tmp", PathLib(temp_voc).name)
        file_manager.delete_file("tmp", PathLib(temp_bg).name)
        file_manager.delete_file("tmp", PathLib(final_mix_wav).name)
        file_manager.delete_file("tmp", PathLib(temp_vid).name)
    except OSError as e:
        logger.warning(f"Cleanup of final temp files failed: {e}")


def execute_pipeline(clips_data: dict, output_path: str):
    """Executes the pipeline using Multi-Stage Chunk Rendering with Padded Handles."""
    clips = clips_data.get("clips", [])
    if not clips:
        return

    clip_blueprints = []
    for clip in clips:
        json_path = clip.replace(".mp4", ".json")
        meta = {}
        try:
            meta = file_manager.read_json("video_chunk", PathLib(json_path).name)
        except Exception:
            pass
        clip_blueprints.append(meta)

    durations = [float(ffmpeg.probe(c)["format"]["duration"]) for c in clips]
    xfade_duration = 0.5
    hook_duration = 1.5

    video_stream = next(
        (
            stream
            for stream in ffmpeg.probe(clips[0])["streams"]
            if stream["codec_type"] == "video"
        ),
        None,
    )
    orig_h = int(video_stream["height"])
    orig_w = int(video_stream["width"])
    fps_fraction = video_stream.get("r_frame_rate", "30/1")
    crop_w = int(orig_h * (9 / 16))
    crop_h = orig_h

    logger.info("Stage 1: Parallel Pre-Processing & Demucs (Padded Chunks)...")
    chunk_vids, chunk_vocals, chunk_bgs = _process_chunks_parallel(
        clips, clip_blueprints, durations, fps_fraction, orig_w, orig_h, crop_w, crop_h
    )

    logger.info("Stage 2: Three-Tier XFADE Stitching...")
    temp_vid, temp_voc, temp_bg, global_punch_ins = _stitch_video_and_audio(
        chunk_vids,
        chunk_vocals,
        chunk_bgs,
        clips,
        clip_blueprints,
        durations,
        output_path,
        hook_duration,
        xfade_duration,
    )

    logger.info("Stage 3: Running Final Audio Mix & WhisperX...")
    bgm_filename = clips_data.get("background_audio_track", "bgm.mp3")
    _apply_final_mix_and_encode(
        temp_vid, temp_voc, temp_bg, global_punch_ins, bgm_filename, output_path
    )

    try:
        for chunk in chunk_vids:
            if chunk and PathLib(chunk).exists():
                file_manager.delete_file("video_chunk", PathLib(chunk).name)
        for chunk in chunk_vocals:
            if chunk and PathLib(chunk).exists():
                file_manager.delete_file("video_chunk", PathLib(chunk).name)
        for chunk in chunk_bgs:
            if chunk and PathLib(chunk).exists():
                file_manager.delete_file("video_chunk", PathLib(chunk).name)
    except OSError as e:
        logger.warning(f"Failed to clean up chunk files: {e}")

    logger.info("Successfully executed Phase 3 Elite Rendering Pipeline.")
