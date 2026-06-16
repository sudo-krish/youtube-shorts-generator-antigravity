from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from core.db.manager import db
import os
import shutil

router = APIRouter()

WORKSPACE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "workspace")
VIDEOS_DIR = os.path.join(WORKSPACE_DIR, "videos")
os.makedirs(VIDEOS_DIR, exist_ok=True)


@router.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    """Uploads a video to the workspace and registers it in the DB."""
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")

        file_path = os.path.join(VIDEOS_DIR, file.filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        video_id = db.videos.create(file.filename, file_path)

        return {
            "status": "success",
            "message": "File uploaded successfully",
            "video_id": video_id,
            "path": file_path,
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/videos")
async def list_videos():
    """Returns a list of all registered videos."""
    videos = db.videos.get_all()
    return {"status": "success", "videos": videos}


@router.get("/download/{video_id}")
async def download_video(video_id: str):
    """Serves a video file by ID."""
    video = db.videos.get(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    if not os.path.exists(video["video_path"]):
        raise HTTPException(status_code=404, detail="Video file missing on disk")

    return FileResponse(video["video_path"])
