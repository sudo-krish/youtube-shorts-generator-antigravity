import os
import numpy as np
from scipy.io import wavfile


def get_bgm_and_sfx_paths(bgm_filename: str = "bgm.mp3"):
    """Returns the paths to the BGM and Impact SFX files if they exist."""
    base_dir = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )
    downloads_dir = os.path.join(base_dir, "downloads")

    bgm_path = os.path.join(downloads_dir, "audio_library", bgm_filename)
    if not os.path.exists(bgm_path):
        # Fallback to older default bgm location
        bgm_path = os.path.join(downloads_dir, bgm_filename)

    sfx_impact_path = os.path.join(downloads_dir, "sfx", "impact.mp3")
    sfx_whoosh_path = os.path.join(downloads_dir, "sfx", "whoosh.mp3")

    return bgm_path, sfx_impact_path, sfx_whoosh_path


def run_demucs(audio_path: str, out_dir: str):
    """Runs Demucs to separate vocals from the audio track and returns the path to the vocals.wav."""
    import subprocess

    cmd = [
        "demucs",
        "--two-stems=vocals",
        "-n",
        "htdemucs",
        "--out",
        out_dir,
        audio_path,
    ]
    subprocess.run(
        cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

    basename = os.path.splitext(os.path.basename(audio_path))[0]
    vocals_path = os.path.join(out_dir, "htdemucs", basename, "vocals.wav")
    bg_path = os.path.join(out_dir, "htdemucs", basename, "no_vocals.wav")

    return vocals_path, bg_path


def build_audio_mix_filter(
    global_punch_ins: list,
    main_audio_path: str,
    vocals_path: str,
    bgm_filename: str = "bgm.mp3",
):
    """Dynamically builds the FFmpeg audio mix filter chain for BGM, main audio, and SFX impacts."""
    bgm_path, sfx_impact_path, sfx_whoosh_path = get_bgm_and_sfx_paths(bgm_filename)
    ffmpeg_args = []

    ffmpeg_args.extend(["-i", main_audio_path])
    main_in = "[0:a]"
    input_idx = 1
    filter_complex = ""

    audio_mix_inputs = []
    amix_weights = []

    if os.path.exists(bgm_path):
        ffmpeg_args.extend(["-i", bgm_path])
        bgm_in = f"[{input_idx}:a]"
        input_idx += 1

        if vocals_path and os.path.exists(vocals_path):
            try:
                sample_rate, data = wavfile.read(vocals_path)
                is_silent = False
                if data.size > 0:
                    max_amp = np.max(np.abs(data))
                    # Assuming 16-bit PCM, silence threshold could be around 500
                    if max_amp < 500:
                        is_silent = True
                else:
                    is_silent = True
            except Exception:
                is_silent = False

            ffmpeg_args.extend(["-i", vocals_path])
            vocals_in = f"[{input_idx}:a]"
            input_idx += 1

            if not is_silent:
                # Audio Ducking using isolated vocals
                filter_complex += f"{bgm_in}{vocals_in}sidechaincompress=threshold=0.08:ratio=4.0:attack=10:release=200[ducked_bgm]"
            else:
                # Bypass sidechain compressor and apply static -10dB dip
                filter_complex += f"{bgm_in}volume=0.3[ducked_bgm]"

            audio_mix_inputs.extend([main_in, "[ducked_bgm]"])
            amix_weights.extend(["1.0", "0.4"])
        else:
            filter_complex += f"{main_in}asplit=2[ca_main][ca_side]; {bgm_in}[ca_side]sidechaincompress=threshold=0.08:ratio=4.0:attack=10:release=200[ducked_bgm]"
            audio_mix_inputs.extend(["[ca_main]", "[ducked_bgm]"])
            amix_weights.extend(["1.0", "0.4"])
    else:
        audio_mix_inputs.append(main_in)
        amix_weights.append("1.0")

    if os.path.exists(sfx_impact_path) and global_punch_ins:
        for i, t in enumerate(global_punch_ins):
            delay_ms = int(t * 1000)
            ffmpeg_args.extend(["-i", sfx_impact_path])
            sfx_in = f"[{input_idx}:a]"
            sfx_out = f"[sfx_i_{i}]"
            prefix = "; " if filter_complex else ""
            filter_complex += f"{prefix}{sfx_in}adelay={delay_ms}|{delay_ms}{sfx_out}"
            audio_mix_inputs.append(sfx_out)
            amix_weights.append("1.5")
            input_idx += 1

    if os.path.exists(sfx_whoosh_path) and global_punch_ins:
        for i, t in enumerate(global_punch_ins):
            # Whoosh starts slightly before the impact
            delay_ms = max(0, int((t - 0.2) * 1000))
            ffmpeg_args.extend(["-i", sfx_whoosh_path])
            sfx_in = f"[{input_idx}:a]"
            sfx_out = f"[sfx_w_{i}]"
            prefix = "; " if filter_complex else ""
            filter_complex += f"{prefix}{sfx_in}adelay={delay_ms}|{delay_ms}{sfx_out}"
            audio_mix_inputs.append(sfx_out)
            amix_weights.append("1.0")
            input_idx += 1

    if len(audio_mix_inputs) > 1:
        mix_inputs_str = "".join(audio_mix_inputs)
        weights_str = " ".join(amix_weights)
        prefix = "; " if filter_complex else ""
        filter_complex += f"{prefix}{mix_inputs_str}amix=inputs={len(audio_mix_inputs)}:duration=first:weights={weights_str}[fouta]"
        audio_map = "[fouta]"
    else:
        audio_map = main_in

    return ffmpeg_args, filter_complex, audio_map
