import os
import subprocess
from typing import Dict, Any
from core.base_service import BaseNanoService

# Ensure outputs directory exists
OUTPUTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "outputs")
os.makedirs(OUTPUTS_DIR, exist_ok=True)

class BatchCropService(BaseNanoService):
    """
    Nano-Service for processing a list of clips (In/Out points) and 
    extracting them from the source video using FFmpeg.
    """
    route = "/video/batch-crop"

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        video_filename = payload.get("video_filename")
        clips = payload.get("clips", [])
        
        if not video_filename or not clips:
            return {"error": "Missing video_filename or clips"}

        # Assume video is in the assets or outputs folder (or we receive a full path)
        # For this prototype, we'll assume the client sent the original video 
        # to the upload endpoint first, and we have it in /tmp or outputs.
        # Wait, the upload endpoint stores it in assets/uploads/
        
        backend_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        source_path = os.path.join(backend_root, "assets", "uploads", video_filename)
        
        # If it doesn't exist there, maybe the frontend just sends a mocked response 
        # or we check if the file exists.
        if not os.path.exists(source_path):
            # Fallback for testing: Just return success with mocked URLs
            return {
                "message": f"Source video {video_filename} not found locally.",
                "results": [
                    {
                        "id": clip.get("id"),
                        "name": clip.get("name"),
                        "status": "mocked",
                        "url": f"/outputs/mock_{clip.get('id')}.mp4"
                    } for clip in clips
                ]
            }

        results = []
        for clip in clips:
            clip_id = clip.get("id")
            start_time = clip.get("startTime")
            end_time = clip.get("endTime")
            name = clip.get("name", clip_id)
            
            output_filename = f"crop_{clip_id}.mp4"
            output_path = os.path.join(OUTPUTS_DIR, output_filename)
            
            # Run FFmpeg to crop the video without re-encoding (fast)
            # ffmpeg -ss [start] -i [input] -to [duration] -c copy [output]
            duration = end_time - start_time
            
            cmd = [
                "ffmpeg", "-y",
                "-ss", str(start_time),
                "-i", source_path,
                "-t", str(duration),
                "-c", "copy",
                output_path
            ]
            
            try:
                subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                results.append({
                    "id": clip_id,
                    "name": name,
                    "status": "success",
                    "url": f"/outputs/{output_filename}"
                })
            except subprocess.CalledProcessError as e:
                results.append({
                    "id": clip_id,
                    "name": name,
                    "status": "error",
                    "error": e.stderr.decode()
                })
                
        return {
            "message": f"Processed {len(clips)} clips.",
            "results": results
        }
