import os

def get_bgm_and_sfx_paths():
    """Returns the paths to the BGM and Impact SFX files if they exist."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    downloads_dir = os.path.join(base_dir, "downloads")
    
    bgm_path = os.path.join(downloads_dir, "bgm.mp3")
    sfx_impact_path = os.path.join(downloads_dir, "sfx", "impact.mp3")
    
    return bgm_path, sfx_impact_path

def build_audio_mix_filter(global_punch_ins: list, filter_complex: str, input_idx: int):
    """Dynamically builds the FFmpeg audio mix filter chain for BGM and requested SFX impacts."""
    bgm_path, sfx_impact_path = get_bgm_and_sfx_paths()
    ffmpeg_args = []
    
    audio_mix_inputs = ["[ca]"]
    amix_weights = "1"
    
    if os.path.exists(bgm_path):
        ffmpeg_args.extend(['-i', bgm_path])
        audio_mix_inputs.append(f"[{input_idx}:a]")
        amix_weights += " 0.2"
        input_idx += 1
        
    if os.path.exists(sfx_impact_path) and global_punch_ins:
        for i, t in enumerate(global_punch_ins):
            delay_ms = int(t * 1000)
            ffmpeg_args.extend(['-i', sfx_impact_path])
            sfx_in = f"[{input_idx}:a]"
            sfx_out = f"[sfx{i}]"
            filter_complex += f"; {sfx_in}adelay={delay_ms}|{delay_ms}{sfx_out}"
            audio_mix_inputs.append(sfx_out)
            amix_weights += " 1.5"
            input_idx += 1
            
    if len(audio_mix_inputs) > 1:
        mix_inputs_str = "".join(audio_mix_inputs)
        filter_complex += f"; {mix_inputs_str}amix=inputs={len(audio_mix_inputs)}:duration=first:weights={amix_weights}[fouta]"
        audio_map = "[fouta]"
    else:
        audio_map = "[ca]"
        
    return ffmpeg_args, filter_complex, audio_map
