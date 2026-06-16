import os
import json
import logging
import subprocess
import ffmpeg
from app.generator.engine import execute_pipeline, _build_visual_filtergraph
from app.generator.qa_gate import run_qa_gate

logger = logging.getLogger(__name__)


def _render_hook_variant(hook_clip: str, base_output_path: str, variant: dict) -> str:
    """Renders a standalone hook with a unique styling filter."""
    hook_out = base_output_path.replace(".mp4", f"_{variant['id']}_hook.mp4")
    logger.info(f"Asset Tree: Rendering Hook {variant['id']}...")

    # Read hook metadata
    json_path = hook_clip.replace(".mp4", ".json")
    meta = {}
    if os.path.exists(json_path):
        with open(json_path, "r") as f:
            meta = json.load(f)

    try:
        video_stream = next(
            s for s in ffmpeg.probe(hook_clip)["streams"] if s["codec_type"] == "video"
        )
        orig_w = int(video_stream["width"])
        orig_h = int(video_stream["height"])
        fps_fraction = video_stream.get("r_frame_rate", "30/1")
    except Exception:
        orig_w, orig_h, fps_fraction = 1920, 1080, "60/1"

    crop_w = int(orig_h * (9 / 16))
    crop_h = orig_h
    hook_duration = meta.get("duration", 1.5)

    # Build the proper cropping/trimming filtergraph
    v_filter_str, _ = _build_visual_filtergraph(
        meta=meta,
        duration=hook_duration,
        fps_fraction=fps_fraction,
        orig_w=orig_w,
        crop_w=crop_w,
        crop_h=crop_h,
        is_hook=True,
        hook_duration=hook_duration,
    )

    # Append the variant styling
    final_vf = f"{v_filter_str},{variant['style']}"

    # We also need to trim the audio to match! The handle_start needs to be trimmed.
    handle_start = meta.get("handle_start", 0.0)
    audio_filter = f"atrim=start={handle_start}:duration={hook_duration},asetpts=PTS-STARTPTS"

    cmd_hook = [
        "ffmpeg",
        "-y",
        "-i",
        hook_clip,
        "-vf",
        final_vf,
        "-af",
        audio_filter,
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-c:a",
        "aac",
        hook_out,
    ]
    subprocess.run(
        cmd_hook, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    return hook_out


def _stitch_variant(
    hook_out: str, body_output_path: str, base_output_path: str, variant: dict
) -> str:
    """Stitches a rendered hook and the cached body together."""
    final_variant_out = base_output_path.replace(".mp4", f"_{variant['id']}.mp4")
    concat_txt = base_output_path.replace(".mp4", f"_{variant['id']}_concat.txt")

    with open(concat_txt, "w") as f:
        f.write(f"file '{os.path.abspath(hook_out)}'\n")
        f.write(f"file '{os.path.abspath(body_output_path)}'\n")

    logger.info(f"Asset Tree: Stitching Variant {variant['id']}...")
    cmd_stitch = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        concat_txt,
        "-c",
        "copy",
        final_variant_out,
    ]

    subprocess.run(
        cmd_stitch, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

    try:
        if os.path.exists(concat_txt):
            os.remove(concat_txt)
    except OSError as e:
        logger.warning(f"Failed to remove concat txt {concat_txt}: {e}")

    return final_variant_out


def generate_asset_tree(clips_data: dict, base_output_path: str) -> list[str]:
    """
    Generates a multi-variant Asset Tree by pre-rendering the body and stitching
    unique hooks for A/B testing variations.
    """
    clips = clips_data.get("clips", [])
    if len(clips) < 2:
        logger.error(
            "Not enough clips to build a tree (need at least 1 hook and 1 body clip)."
        )
        return [base_output_path]

    hook_clip = clips[0]
    body_clips = clips[1:]

    # 1. Pre-render the Body (cached)
    body_output_path = base_output_path.replace(".mp4", "_body_cache.mp4")

    logger.info("Asset Tree: Generating Cached Body...")
    body_clips_data = {
        "clips": body_clips,
        "background_audio_track": clips_data.get("background_audio_track", "bgm.mp3"),
    }

    try:
        execute_pipeline(body_clips_data, body_output_path)
    except Exception as e:
        logger.error(f"Failed to generate body cache: {e}")
        return []

    # 2. Render 3 Hook Variations
    hook_variations = [
        {"id": "hookA", "style": "eq=contrast=1.3:saturation=1.5"},  # High Energy
        {"id": "hookB", "style": "eq=saturation=0.1:gamma=0.9"},  # B&W / Bleak
        {"id": "hookC", "style": "colorbalance=rs=.2:rm=.2:rh=.2"},  # Warm / Glowing
    ]

    final_outputs = []

    for variant in hook_variations:
        hook_out = _render_hook_variant(hook_clip, base_output_path, variant)
        final_variant_out = _stitch_variant(
            hook_out, body_output_path, base_output_path, variant
        )

        # Run QA Gate
        if run_qa_gate(final_variant_out):
            final_outputs.append(final_variant_out)
        else:
            logger.error(f"QA Gate Failed for {final_variant_out}")

        try:
            if os.path.exists(hook_out):
                os.remove(hook_out)
        except OSError as e:
            logger.warning(f"Failed to cleanup hook_out {hook_out}: {e}")

    # Cleanup Body Cache
    try:
        if os.path.exists(body_output_path):
            os.remove(body_output_path)
    except OSError as e:
        logger.warning(f"Failed to cleanup body cache {body_output_path}: {e}")

    logger.info(
        f"Successfully generated Asset Tree: {len(final_outputs)} variants created."
    )
    return final_outputs
