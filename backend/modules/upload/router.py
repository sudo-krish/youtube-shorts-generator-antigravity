from fastapi import APIRouter, UploadFile, File, HTTPException
import os
import shutil
import uuid
import logging
from core.settings import ASSETS_DIR

router = APIRouter(tags=["upload"])
logger = logging.getLogger(__name__)

@router.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    if not file.filename.endswith(".mp4"):
        raise HTTPException(status_code=400, detail="Only .mp4 files are supported.")
        
    try:
        # Create assets directory if it doesn't exist
        os.makedirs(ASSETS_DIR, exist_ok=True)
        
        # We can either use a uuid or the original filename. The frontend uses the filename in onUploadComplete.
        # But to prevent collisions, we can keep the original name since this is a local processing tool.
        file_path = os.path.join(ASSETS_DIR, file.filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        video_id = file.filename.replace(".mp4", "")
        
        logger.info(f"Video uploaded successfully: {file_path}")
        return {
            "status": "success", 
            "video_id": video_id,
            "video_path": file_path
        }
    except Exception as e:
        logger.error(f"Error uploading video: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/videos")
async def list_uploaded_videos():
    try:
        os.makedirs(ASSETS_DIR, exist_ok=True)
        files = []
        for filename in os.listdir(ASSETS_DIR):
            if filename.endswith(".mp4"):
                filepath = os.path.join(ASSETS_DIR, filename)
                files.append({
                    "video_id": filename.replace(".mp4", ""),
                    "filename": filename,
                    "video_path": filepath,
                    "modified": os.path.getmtime(filepath)
                })
        # Sort by modified time, newest first
        files.sort(key=lambda x: x["modified"], reverse=True)
        return {"status": "success", "videos": files}
    except Exception as e:
        logger.error(f"Error listing uploaded videos: {e}")
        raise HTTPException(status_code=500, detail=str(e))
