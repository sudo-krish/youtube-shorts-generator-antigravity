import os
import hashlib
import time
import shutil
from fastapi import UploadFile
from core.db.manager import db
from core.settings import VIDEOS_DIR

def get_hashed_filename(filename: str) -> str:
    """Generates a unique but deterministic ID for a file based on its name."""
    return hashlib.md5(filename.encode('utf-8')).hexdigest()

def check_video_exists(video_id: str) -> dict:
    """Checks the database to see if a video already exists."""
    row = db.videos.get(video_id)
    if row:
        return {"exists": True, "video_id": row["video_id"], "video_name": row["video_name"], "video_path": row["video_path"]}
    return {"exists": False}

async def handle_video_upload(file: UploadFile) -> dict:
    """Handles the physical upload, deduplication, and database entry."""
    filename = file.filename
    video_id = get_hashed_filename(filename)
    
    # Deduplication check
    existing = check_video_exists(video_id)
    if existing["exists"]:
        return existing
        
    # File doesn't exist, proceed to save
    video_path = os.path.join(str(VIDEOS_DIR), f"{video_id}.mp4")
    
    with open(video_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Insert into database
    db.videos.create(video_id, filename, video_path)
    
    return {"exists": False, "video_id": video_id, "video_name": filename, "video_path": video_path}
