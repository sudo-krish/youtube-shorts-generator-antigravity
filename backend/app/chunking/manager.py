import os
import uuid
import ffmpeg
import logging
from core.db.manager import db
from core.settings import VIDEO_CHUNKS_DIR, AUDIO_CHUNKS_DIR
from app.audio_extractor.manager import extract_audio_chunk

logger = logging.getLogger(__name__)

def get_or_create_chunk(video_id: str, chunk_index: int, video_path: str, chunk_duration: int = 15):
    """Validates if a chunk exists in the DB and filesystem. If not, generates video and audio slices."""
    
    row = db.chunks.get_by_index(video_id, chunk_index)
    
    if row:
        chunk_id = row["chunk_id"]
        chunk_name = row["chunk_name"]
        audio_chunk_name = row.get("audio_chunk_name")
        
        chunk_path = os.path.join(str(VIDEO_CHUNKS_DIR), chunk_name)
        
        # Check Filesystem
        if os.path.exists(chunk_path):
            logger.info(f"Chunk Cache Hit: {chunk_path}")
            
            # Ensure audio is generated if missing from older DB versions
            if not audio_chunk_name or not os.path.exists(os.path.join(str(AUDIO_CHUNKS_DIR), audio_chunk_name)):
                audio_chunk_name = f"{video_id}_{chunk_index}.wav"
                audio_path = os.path.join(str(AUDIO_CHUNKS_DIR), audio_chunk_name)
                start_time = chunk_index * chunk_duration
                extract_audio_chunk(video_path, start_time, chunk_duration, audio_path)
                db.chunks.update_audio_name(chunk_id, audio_chunk_name)
            else:
                audio_path = os.path.join(str(AUDIO_CHUNKS_DIR), audio_chunk_name)
                
            return chunk_path, audio_path
        else:
            logger.warning(f"Chunk Cache Miss (DB stale): {chunk_path}. Regenerating...")
            db.chunks.delete(chunk_id)

    # Need to generate
    chunk_id = str(uuid.uuid4())
    chunk_name = f"{video_id}_{chunk_index}.mp4"
    audio_chunk_name = f"{video_id}_{chunk_index}.wav"
    
    chunk_path = os.path.join(str(VIDEO_CHUNKS_DIR), chunk_name)
    audio_path = os.path.join(str(AUDIO_CHUNKS_DIR), audio_chunk_name)
    start_time = chunk_index * chunk_duration
    
    logger.info(f"FFmpeg Slicing: Generating chunk {chunk_index} for {video_id}...")
    try:
        # Video Slice
        (
            ffmpeg.input(video_path, ss=start_time, t=chunk_duration)
            .output(chunk_path, vcodec="libx264", acodec="aac", preset="ultrafast", max_muxing_queue_size=1024)
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        
        # Audio Slice
        extract_audio_chunk(video_path, start_time, chunk_duration, audio_path)
        
        db.chunks.create(chunk_id, video_id, chunk_index, chunk_name, audio_chunk_name, start_time, chunk_duration)
    except ffmpeg.Error as e:
        logger.error(f"FFmpeg slice error: {e.stderr.decode()}")
        raise Exception("Failed to chunk video.")

    return chunk_path, audio_path
