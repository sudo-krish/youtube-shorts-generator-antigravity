import os
import logging
import subprocess
from backend.pipeline.engine import execute_pipeline
from backend.pipeline.qa_gate import run_qa_gate

logger = logging.getLogger(__name__)


def _render_hook_variant(hook_clip: str, base_output_path: str, variant: dict) -> str:
    """Renders a standalone hook with a unique styling filter."""
    hook_out = base_output_path.replace(".mp4", f"_{variant['id']}_hook.mp4")
    logger.info(f"Asset Tree: Rendering Hook {variant['id']}...")

    cmd_hook = [
        "ffmpeg",
        "-y",
        "-i",
        hook_clip,
        "-vf",
        f"scale=1080:1920,fps=60,{variant['style']}",
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
        {"id": "hookA", "style": "eq=contrast=1.5:saturation=1.5"},  # High Energy
        {"id": "hookB", "style": "hue=h=90:s=1.0"},  # Psychedelic/Curiosity
        {
            "id": "hookC",
            "style": "colorchannelmixer=.3:.4:.3:0:.3:.4:.3:0:.3:.4:.3",
        },  # B&W / Direct
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
