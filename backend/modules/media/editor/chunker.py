import os
import uuid
import logging
import subprocess
from core.base_service import BaseNanoService

logger = logging.getLogger(__name__)

class ChunkerService(BaseNanoService):
    """
    Nano-Service: POST /api/media/editor/chunker
    Extracts a time-sliced chunk from a video using FFmpeg.
    Payload expected: {
        "video_path": str,
        "start_time": float,
        "duration": float
    }
    """
    
    def execute(self, payload: dict) -> dict:
        video_path = payload.get("video_path")
        start_time = payload.get("start_time", 0.0)
        duration = payload.get("duration", 15.0)
        
        if not video_path or not os.path.exists(video_path):
            logger.error(f"Chunker failed: Invalid video_path {video_path}")
            return {"status": "error", "message": "Invalid video_path"}
            
        try:
            chunks_dir = "/tmp/chunks"
            os.makedirs(chunks_dir, exist_ok=True)
            
            chunk_filename = f"chunk_{uuid.uuid4().hex[:8]}.mp4"
            chunk_path = os.path.join(chunks_dir, chunk_filename)
            
            # Fast exact copy (no re-encoding)
            # We place -ss before -i for fast seeking, and -t for duration
            cmd = [
                "ffmpeg", "-y", 
                "-ss", str(start_time),
                "-i", video_path,
                "-t", str(duration),
                "-c", "copy",
                chunk_path
            ]
            
            logger.info(f"Running ffmpeg chunker: {' '.join(cmd)}")
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            if result.returncode != 0:
                logger.error(f"FFmpeg error: {result.stderr}")
                return {"status": "error", "message": "FFmpeg slicing failed", "details": result.stderr}
                
            return {
                "status": "success", 
                "chunk_path": chunk_path,
                "start_time": start_time,
                "duration": duration
            }
        except Exception as e:
            logger.error(f"Chunk processing failed: {e}")
            return {"status": "error", "error": str(e)}
