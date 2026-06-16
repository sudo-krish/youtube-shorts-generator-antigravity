from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import logging
import uuid
import time
import json
import httpx
import os
from core.db.manager import db
from app.chunking.manager import get_or_create_chunk
from utils.visualizer import create_yolo_overlay_video
from core.settings import TMP_DIR

router = APIRouter(tags=["testing"])
logger = logging.getLogger(__name__)

class TestRunRequest(BaseModel):
    video_id: str
    chunk_index: int
    transformer_name: str
    game_id: Optional[str] = "valorant"

class TestRecord(BaseModel):
    test_id: str
    video_id: str
    chunk_index: int
    transformer_name: str
    status: str
    start_time: float
    end_time: Optional[float]
    output_data: Optional[str]
    visual_output_path: Optional[str]

@router.get("/", response_model=List[TestRecord])
def get_all_tests():
    rows = db.tests.get_all()
    results = []
    for r in rows:
        results.append(TestRecord(
            test_id=r["test_id"],
            video_id=r["video_id"],
            chunk_index=r["chunk_index"],
            transformer_name=r["transformer_name"],
            status=r["status"],
            start_time=r["start_time"],
            end_time=r["end_time"],
            output_data=r["output_data"],
            visual_output_path=r["visual_output_path"]
        ))
    return results

def run_test_background(test_id: str, video_id: str, chunk_index: int, transformer_name: str, game_id: str):
    try:
        # 1. Get original video path
        video_record = db.videos.get(video_id)
        if not video_record:
            raise Exception("Video not found in DB")
        video_path = video_record["video_path"]
        
        # 2. Get or create chunk
        chunk_path, _ = get_or_create_chunk(video_id, chunk_index, video_path)
        
        # 3. Call transformer API
        api_url = f"http://127.0.0.1:8000/api/transformers/{transformer_name}"
        payload = {
            "video_path": chunk_path,
            "duration": 15.0, # Default chunk size
            "step": 1 if transformer_name == "yolo" else 3,
            "game_id": game_id
        }
        
        response = httpx.post(api_url, json=payload, timeout=600)
        response.raise_for_status()
        matrix_data = response.json().get("matrix", [])
        
        visual_path = None
        
        # 4. Generate visual overlay if YOLO
        if transformer_name == "yolo":
            visual_path = os.path.join(str(TMP_DIR), f"yolo_overlay_{test_id}.mp4")
            create_yolo_overlay_video(chunk_path, visual_path, matrix_data)
            
        # 5. Success
        db.tests.update(test_id, 'success', json.dumps(matrix_data), visual_path)
        
    except Exception as e:
        logger.error(f"Test run failed: {e}")
        db.tests.update(test_id, 'error', str(e))

@router.post("/run")
def start_test_run(req: TestRunRequest, background_tasks: BackgroundTasks):
    test_id = str(uuid.uuid4())
    
    db.tests.create(test_id, req.video_id, req.chunk_index, req.transformer_name)
    
    background_tasks.add_task(
        run_test_background,
        test_id, req.video_id, req.chunk_index, req.transformer_name, req.game_id
    )
    
    return {"status": "started", "test_id": test_id}
