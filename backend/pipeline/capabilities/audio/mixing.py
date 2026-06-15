import os

def get_bgm_and_sfx_paths(bgm_filename: str = "bgm.mp3"):
    """Returns the paths to the BGM and Impact SFX files if they exist."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    downloads_dir = os.path.join(base_dir, "downloads")
    
    bgm_path = os.path.join(downloads_dir, "audio_library", bgm_filename)
    if not os.path.exists(bgm_path):
        # Fallback to older default bgm location
        bgm_path = os.path.join(downloads_dir, bgm_filename)
        
    sfx_impact_path = os.path.join(downloads_dir, "sfx", "impact.mp3")
    sfx_whoosh_path = os.path.join(downloads_dir, "sfx", "whoosh.mp3")
    
    return bgm_path, sfx_impact_path, sfx_whoosh_path

def build_audio_mix_filter(global_punch_ins: list, filter_complex: str, input_idx: int, bgm_filename: str = "bgm.mp3"):
    """Dynamically builds the FFmpeg audio mix filter chain for BGM and requested SFX impacts."""
    bgm_path, sfx_impact_path, sfx_whoosh_path = get_bgm_and_sfx_paths(bgm_filename)
    ffmpeg_args = []
    
    audio_mix_inputs = []
    amix_weights = []
    
    if os.path.exists(bgm_path):
        ffmpeg_args.extend(['-i', bgm_path])
        bgm_in = f"[{input_idx}:a]"
        input_idx += 1
        
        # Audio Ducking: Split main audio, feed one side to sidechaincompress with BGM
        # threshold=0.08 means when main audio gets reasonably loud, it squashes the BGM
        filter_complex += f"; [ca]asplit=2[ca_main][ca_side]; {bgm_in}[ca_side]sidechaincompress=threshold=0.08:ratio=4.0:attack=10:release=200[ducked_bgm]"
        audio_mix_inputs.extend(["[ca_main]", "[ducked_bgm]"])
        amix_weights.extend(["1.0", "0.4"]) # BGM baseline is 0.4 volume, ducked lower during talking
    else:
        audio_mix_inputs.append("[ca]")
        amix_weights.append("1.0")
        
    if os.path.exists(sfx_impact_path) and global_punch_ins:
        for i, t in enumerate(global_punch_ins):
            delay_ms = int(t * 1000)
            ffmpeg_args.extend(['-i', sfx_impact_path])
            sfx_in = f"[{input_idx}:a]"
            sfx_out = f"[sfx_i_{i}]"
            filter_complex += f"; {sfx_in}adelay={delay_ms}|{delay_ms}{sfx_out}"
            audio_mix_inputs.append(sfx_out)
            amix_weights.append("1.5")
            input_idx += 1
            
    if os.path.exists(sfx_whoosh_path) and global_punch_ins:
        for i, t in enumerate(global_punch_ins):
            # Whoosh starts slightly before the impact
            delay_ms = max(0, int((t - 0.2) * 1000))
            ffmpeg_args.extend(['-i', sfx_whoosh_path])
            sfx_in = f"[{input_idx}:a]"
            sfx_out = f"[sfx_w_{i}]"
            filter_complex += f"; {sfx_in}adelay={delay_ms}|{delay_ms}{sfx_out}"
            audio_mix_inputs.append(sfx_out)
            amix_weights.append("1.0")
            input_idx += 1
            
    if len(audio_mix_inputs) > 1:
        mix_inputs_str = "".join(audio_mix_inputs)
        weights_str = " ".join(amix_weights)
        filter_complex += f"; {mix_inputs_str}amix=inputs={len(audio_mix_inputs)}:duration=first:weights={weights_str}[fouta]"
        audio_map = "[fouta]"
    else:
        # If no BGM and no SFX, handle the case where we didn't use asplit
        audio_map = "[ca]"
        
    return ffmpeg_args, filter_complex, audio_map
