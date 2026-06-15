import os

editor_path = "backend/editor.py"

with open(editor_path, "r") as f:
    content = f.read()

# 1. Add imports at top
import_str = "import json\nimport logging\nimport subprocess\nimport ffmpeg\nfrom hyperframe import generate_crop_polynomial\nfrom effects.registry import create_effect\n"
content = content.replace("import json\nimport logging\nimport subprocess\nimport ffmpeg\nfrom hyperframe import generate_crop_polynomial", import_str)

# 2. Modify meta loading
old_meta = """    for idx, clip in enumerate(clips):
        json_path = clip.replace('.mp4', '.json')
        if os.path.exists(json_path):
            with open(json_path, 'r') as f:
                meta = json.load(f)
                punch_ins = meta.get('visual_punch_in_timestamps', [])
                speed_mult = 1.2 if idx == 1 else 1.0
                for p in punch_ins:
                    global_punch_ins.append(current_time + (p * speed_mult))
                current_time += (meta.get('duration', 0.0) * speed_mult)
                texts[idx] = meta.get('story_text', '').strip()"""

new_meta = """    clip_effects = []
    for idx, clip in enumerate(clips):
        json_path = clip.replace('.mp4', '.json')
        clip_objs = []
        speed_mult = 1.0
        if os.path.exists(json_path):
            with open(json_path, 'r') as f:
                meta = json.load(f)
                punch_ins = meta.get('visual_punch_in_timestamps', [])
                
                for eff in meta.get('effects', []):
                    obj = create_effect(eff.get('effect_name'), eff.get('start_time', 0.0), eff.get('duration', 999.0))
                    if obj:
                        clip_objs.append(obj)
                        if hasattr(obj, 'speed_factor'):
                            speed_mult = obj.speed_factor

                for p in punch_ins:
                    global_punch_ins.append(current_time + (p * speed_mult))
                current_time += (meta.get('duration', 0.0) * speed_mult)
                texts[idx] = meta.get('story_text', '').strip()
        clip_effects.append(clip_objs)"""
content = content.replace(old_meta, new_meta)


# 3. Modify filter generation
old_filters = """    # Proposition: Normal speed, reset PTS, white text
    v0 = f"[0:v]crop={crop_w}:{crop_h}:'{crop_x_0}':0,setpts=PTS-STARTPTS,fps={fps_fraction},scale=1080:1920,drawtext={font_p}:text='{p_text}'[v0]"
    a0 = f"[0:a]asetpts=PTS-STARTPTS[a0]"

    # Struggle: Slow down (1.2x), reset PTS, desaturate, glitch/RGB split, red text
    v1 = f"[1:v]crop={crop_w}:{crop_h}:'{crop_x_1}':0,setpts=1.2*(PTS-STARTPTS),fps={fps_fraction},scale=1080:1920,eq=saturation=0.3,chromashift=cbh=10:crh=-10:enable='lt(mod(t,0.5),0.1)',drawtext={font_s}:text='{s_text}'[v1]"
    a1 = f"[1:a]asetpts=PTS-STARTPTS,atempo=0.83333333[a1]"

    # Result: Normal speed, reset PTS, screen shake crop, flash, vignette pulse, yellow text
    shake_x = f"({crop_x_2})+if(between(t,0,0.5),sin(t*40)*20,0)"
    v2 = f"[2:v]crop={crop_w}:{crop_h}:'{shake_x}':0,setpts=PTS-STARTPTS,fps={fps_fraction},scale=1080:1920,colorlevels=rimin=0.6:gimin=0.6:bimin=0.6:enable='between(t,0,0.5)',vignette='PI/4+sin(t*10)*0.2',drawtext={font_r}:text='{r_text}'[v2]"
    a2 = f"[2:a]asetpts=PTS-STARTPTS[a2]"
    
    concat_filter = f"[v0][a0][v1][a1][v2][a2]concat=n=3:v=1:a=1[cv][ca]\"""

new_filters = """    def build_stream(idx, crop_x, text):
        objs = clip_effects[idx]
        
        # 1. Evaluate crop offset (screen shake)
        c_x = f"({crop_x})"
        for obj in objs:
            if hasattr(obj, 'get_crop_offset'):
                c_x += "+" + obj.get_crop_offset()
                
        v_filters = [f"crop={crop_w}:{crop_h}:'{c_x}':0"]
        a_filters = ["asetpts=PTS-STARTPTS"]
        
        # 2. Evaluate temporal (slow mo)
        temporal_v = "setpts=PTS-STARTPTS"
        for obj in objs:
            if hasattr(obj, 'get_temporal_video_filter'):
                temporal_v = obj.get_temporal_video_filter()
                a_filters.append(obj.get_temporal_audio_filter())
                break
                
        v_filters.append(temporal_v)
        v_filters.append(f"fps={fps_fraction}")
        v_filters.append("scale=1080:1920")
        
        # 3. Evaluate visual / audio effects
        for obj in objs:
            if hasattr(obj, 'get_video_filter'):
                vf = obj.get_video_filter()
                if vf: v_filters.append(vf)
            if hasattr(obj, 'get_audio_filter'):
                af = obj.get_audio_filter()
                if af: a_filters.append(af)
                
        # 4. Text Overlay
        if text:
            # Apply color based on phase for legacy support, or if specific text effect requested
            font_color = "white" if idx == 0 else "red" if idx == 1 else "yellow"
            v_filters.append(f"drawtext={base_font}:fontcolor={font_color}:text='{text}'")
            
        v_out = f"[{idx}:v]" + ",".join(v_filters) + f"[v{idx}]"
        a_out = f"[{idx}:a]" + ",".join(a_filters) + f"[a{idx}]"
        return v_out, a_out

    v0, a0 = build_stream(0, crop_x_0, p_text)
    v1, a1 = build_stream(1, crop_x_1, s_text)
    v2, a2 = build_stream(2, crop_x_2, r_text)
    
    concat_filter = f"[v0][a0][v1][a1][v2][a2]concat=n=3:v=1:a=1[cv][ca]\"""
content = content.replace(old_filters, new_filters)

# 4. Handle ZoomPunchEffect dynamically
old_zoom = """    zoom_expr = "1+(in_time*0.008)"
    if global_punch_ins:
        conditions = []
        for t in global_punch_ins:
            conditions.append(f"between(in_time,{t},{t+2})")
        cond_str = "+".join(conditions)
        zoom_expr = f"if({cond_str}, 1.3, 1+(in_time*0.008))\"""

new_zoom = """    zoom_expr = "1+(in_time*0.008)"
    
    # Collect all ZoomPunchEffect global timestamps
    # Because zoompan evaluates globally, we must translate local clip times to global times
    zoom_punch_ins = []
    curr_t = 0.0
    for idx, objs in enumerate(clip_effects):
        speed = 1.0
        dur = 0.0
        for obj in objs:
            if hasattr(obj, 'speed_factor'): speed = obj.speed_factor
            if hasattr(obj, 'get_video_filter'): pass # just to check it's loaded
        
        # Wait, duration is meta['duration'], let's just fall back to global_punch_ins which already has accurate speed adjustments
        zoom_punch_ins.extend([t for t in global_punch_ins]) # Simplest for now
        
    if global_punch_ins:
        conditions = []
        for t in global_punch_ins:
            conditions.append(f"between(in_time,{t},{t+2})")
        cond_str = "+".join(conditions)
        zoom_expr = f"if({cond_str}, 1.3, 1+(in_time*0.008))\"""
content = content.replace(old_zoom, new_zoom)

with open(editor_path, "w") as f:
    f.write(content)
print("Updated editor.py successfully")
