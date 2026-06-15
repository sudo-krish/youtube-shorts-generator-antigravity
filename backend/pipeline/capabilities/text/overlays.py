import logging
import textwrap
import whisperx

logger = logging.getLogger(__name__)

def build_drawtext_filter(text: str, start_time: float, duration: float) -> str:
    """Builds a FFmpeg drawtext filter string for narrative story text with auto-wrapping."""
    if not text:
        return ""
        
    font_path = "/usr/share/fonts/truetype/msttcorefonts/Impact.ttf" # Or generic
    safe_text = text.replace("'", "").replace(":", "\\:").replace(",", "\\,")
    
    # Auto-wrap text so it doesn't run off the screen
    wrapped_lines = textwrap.wrap(safe_text, width=22)
    final_text = r"\n".join(wrapped_lines)
    
    end_time = start_time + duration
    enable_expr = f"between(t,{start_time},{end_time})"
    
    # Text drops down from top and has a polished TikTok-style aesthetic
    base_font = f"fontfile='{font_path}':text='{final_text}':fontcolor=white:borderw=5:bordercolor=black:shadowcolor=black@0.9:shadowx=6:shadowy=6:fontsize=75:box=1:boxcolor=black@0.5:boxborderw=25"
    pos_expr = f"x=(w-text_w)/2:y='if(lt(t,{start_time}+0.3), h*0.65 + ({start_time}+0.3-t)*150, h*0.65)'"
    
    return f"drawtext={base_font}:{pos_expr}:enable='{enable_expr}'"

def generate_ass_subtitles(word_segments, output_file="captions.ass"):
    """Generates an Advanced SubStation Alpha (.ass) file for dynamic, ANIMATED word-by-word captions."""
    logger.info(f"Generating Animated ASS subtitles to {output_file} with {len(word_segments)} words.")
    ass_header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Pop,Arial,90,&H0000FFFF,&H000000FF,&H00000000,&H00800000,-1,0,0,0,100,100,0,0,1,8,4,5,10,10,150,1

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
                
                # The "Hormozi Pop": Starts at 50% scale, scales to 120% in 50ms, then settles to 100% in next 50ms.
                pop_anim = r"{\fscx50\fscy50\t(0,50,\fscx120\fscy120)\t(50,100,\fscx100\fscy100)}"
                
                f.write(f"Dialogue: 0,{start_t},{end_t},Pop,,0,0,0,,{pop_anim}{word}\n")

def run_whisperx(audio_path: str, ass_file: str):
    """Runs WhisperX to extract word-level alignments and generates the .ass file."""
    device = "cpu"
    model = whisperx.load_model("base", device)
    audio = whisperx.load_audio(audio_path)
    result = model.transcribe(audio, batch_size=16)

    model_a, metadata = whisperx.load_align_model(language_code=result["language"], device=device)
    result = whisperx.align(result["segments"], model_a, metadata, audio, device, return_char_alignments=False)

    all_words = []
    for segment in result["segments"]:
        if "words" in segment:
            all_words.extend(segment["words"])

    generate_ass_subtitles(all_words, ass_file)
