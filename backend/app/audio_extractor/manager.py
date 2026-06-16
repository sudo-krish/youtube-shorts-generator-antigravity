import ffmpeg
import logging

logger = logging.getLogger(__name__)

def extract_audio_chunk(video_path: str, start_time: float, duration: float, output_audio_path: str) -> str:
    """
    Rips an independent, high-quality audio file from a segment of video using FFmpeg.
    """
    logger.info(f"FFmpeg Audio Extraction: Ripping chunk {output_audio_path} from {start_time} to {start_time + duration}...")
    try:
        (
            ffmpeg.input(video_path, ss=start_time, t=duration)
            .output(output_audio_path, acodec="pcm_s16le", ar="16000", ac=1)
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
    except ffmpeg.Error as e:
        logger.error(f"FFmpeg audio slice error: {e.stderr.decode()}")
        raise Exception("Failed to chunk audio.")
    
    return output_audio_path
