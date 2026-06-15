import os
import json
import asyncio
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import sys
from dotenv import load_dotenv
import urllib.request
import subprocess

load_dotenv()

import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

WORKSPACE_DIR = os.path.join(os.path.dirname(__file__), "workspace")
SFX_DIR = os.path.join(WORKSPACE_DIR, "sfx")
OUTPUTS_DIR = os.path.join(os.path.dirname(__file__), "outputs")
os.makedirs(WORKSPACE_DIR, exist_ok=True)
os.makedirs(SFX_DIR, exist_ok=True)
os.makedirs(OUTPUTS_DIR, exist_ok=True)

import random
import hashlib
import uuid

# Modular Architecture Imports
from ai_director.reviewer import AIReviewer
from generator.cutter import generate_files_from_json
from pipeline.engine import execute_pipeline
from database import init_db, create_job, update_job_status, get_all_jobs, get_job_stages, get_job, create_video, get_video

USAGE_FILE = os.path.join(OUTPUTS_DIR, "usage_tracking.json")

app = FastAPI(title="Hyper Shorts Factory API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- WebSocket Log Streaming ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                pass

manager = ConnectionManager()
main_loop = None

class WebSocketLogHandler(logging.Handler):
    def emit(self, record):
        msg = self.format(record)
        if main_loop and main_loop.is_running():
            try:
                asyncio.run_coroutine_threadsafe(manager.broadcast(msg), main_loop)
            except Exception:
                pass

ws_handler = WebSocketLogHandler()
ws_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logging.getLogger().addHandler(ws_handler)

@app.on_event("startup")
async def startup_event():
    global main_loop
    main_loop = asyncio.get_running_loop()
    init_db()

@app.websocket("/api/logs")
async def websocket_logs(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
# -------------------------------

@app.post("/api/upload")
async def upload_video(file: UploadFile = File(...)):
    logger.info(f"Received upload request for {file.filename}")
    if not file.filename.endswith('.mp4'):
        logger.error(f"Invalid file type: {file.filename}")
        raise HTTPException(status_code=400, detail="Only .mp4 files are supported.")
        
    video_id = str(uuid.uuid4())
    file_location = os.path.join(WORKSPACE_DIR, f"{video_id}.mp4")
    with open(file_location, "wb") as f:
        f.write(await file.read())
    
    create_video(video_id, file.filename, file_location)
    logger.info(f"Saved file {file.filename} to {file_location} as video_id {video_id}")
    return {"status": "success", "video_id": video_id}

class AnalyzeRequest(BaseModel):
    video_id: str
    metadata: dict = {}

def run_orchestrator_job(job_id: str, video_path: str, metadata: dict, resume_state: dict = None):
    job_logger = logging.getLogger(job_id)
    if not any(isinstance(h, logging.FileHandler) for h in job_logger.handlers):
        log_dir = os.path.join(OUTPUTS_DIR, "logs")
        os.makedirs(log_dir, exist_ok=True)
        fh = logging.FileHandler(os.path.join(log_dir, f"{job_id}.log"))
        fh.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        job_logger.addHandler(fh)
        job_logger.setLevel(logging.INFO)
        
    try:
        job_logger.info(f"Starting orchestrator for job {job_id} on video {video_path}")
        # Stage 1: AI Director
        reviewer = AIReviewer(video_path=video_path, metadata=metadata)
        output_json = reviewer.review_video(job_id, resume_state=resume_state)
        
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        output_path = os.path.join(WORKSPACE_DIR, f"{base_name}_segments.json")
        with open(output_path, "w") as f:
            json.dump(output_json, f, indent=2)
            
        job_logger.info(f"AI Analysis Complete! Saved categorization to {output_path}")
        update_job_status(job_id, "completed", json_path=output_path)
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        job_logger.error(f"Error in background task: {e}")
        update_job_status(job_id, f"failed: {str(e)}")

from ai_director.config_manager import get_config, set_config

@app.get("/api/config")
async def fetch_config():
    return get_config()

class ConfigUpdate(BaseModel):
    models: dict

@app.post("/api/config")
async def update_config(config: ConfigUpdate):
    set_config(config.model_dump())
    return {"status": "success"}

@app.get("/api/models")
async def get_models():
    try:
        import google.genai as genai
        client = genai.Client()
        models = [m.name for m in client.models.list()]
        gemini_models = sorted([m.replace("models/", "") for m in models if "gemini" in m and "vision" not in m])
        if not gemini_models:
            raise Exception("No gemini models found")
        return {"status": "success", "models": gemini_models}
    except Exception as e:
        logger.error(f"Failed to fetch models: {e}")
        return {"status": "success", "models": ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]}

@app.post("/api/analyze")
async def analyze_video(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    logger.info(f"Starting async AI analysis on video {request.video_id} with metadata {request.metadata}...")
    
    video = get_video(request.video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    job_id = str(uuid.uuid4())
    create_job(job_id, request.video_id)
    
    # Note: create_job now saves the metadata in the DB.
    
    background_tasks.add_task(
        run_orchestrator_job,
        job_id=job_id,
        video_path=video["video_path"],
        metadata=request.metadata
    )
    
    return {"job_id": job_id, "status": "processing"}

@app.post("/api/redrive/{job_id}")
async def redrive_job(job_id: str, background_tasks: BackgroundTasks):
    logger.info(f"Redriving job {job_id}...")
    
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    completed_stages = get_completed_stages(job_id)
    agents_dir = os.path.join(OUTPUTS_DIR, "agents", job_id)
    resume_state = {}
    
    if os.path.exists(agents_dir):
        for stage_name in completed_stages:
            file_path = os.path.join(agents_dir, f"{stage_name}.txt")
            if os.path.exists(file_path):
                with open(file_path, "r") as f:
                    try:
                        resume_state[stage_name] = json.load(f)
                    except Exception:
                        f.seek(0)
                        resume_state[stage_name] = f.read()
    
    update_job_status(job_id, "processing")
    
    background_tasks.add_task(
        run_orchestrator_job,
        job_id=job_id,
        video_path=job["video_path"],
        metadata=job.get("metadata", {}),
        resume_state=resume_state
    )
    
    return {"job_id": job_id, "status": "processing", "message": "Redrive initiated"}

@app.get("/api/jobs")
async def list_jobs_endpoint():
    return {"status": "success", "jobs": get_all_jobs()}

@app.get("/api/jobs/{job_id}/stages")
async def list_job_stages_endpoint(job_id: str):
    return {"status": "success", "stages": get_job_stages(job_id)}

@app.get("/api/jobs/{job_id}/status")
async def get_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    stages = get_job_stages(job_id)
    # Reconstruct backwards compatibility format for now if needed, or return DB format
    return {
        "status": job["status"],
        "json_path": job["json_path"],
        "video_path": job["video_path"],
        "agent_states": stages
    }

@app.get("/api/jobs/{job_id}/logs")
async def get_job_logs(job_id: str):
    log_path = os.path.join(OUTPUTS_DIR, "logs", f"{job_id}.log")
    if not os.path.exists(log_path):
        return {"status": "success", "logs": "No logs generated yet."}
    with open(log_path, "r") as f:
        logs = f.read()
    return {"status": "success", "logs": logs}

class SpliceRequest(BaseModel):
    video_path: str
    json_path: str

@app.post("/api/splice")
async def splice_video(request: SpliceRequest, background_tasks: BackgroundTasks):
    logger.info(f"Received splice request for {request.video_path}")
    if not os.path.exists(request.video_path) or not os.path.exists(request.json_path):
        logger.error("Files not found for splice")
        raise HTTPException(status_code=404, detail="Files not found")
        
    logger.info("Stage 2: File Generator starting...")
    with open(request.json_path, 'r') as f:
        data = json.load(f)
        
    background_tasks.add_task(generate_files_from_json, request.video_path, data)
    return {"status": "success", "message": "Splicing started in background!"}

@app.get("/api/projects")
async def list_projects():
    projects = []
    for file in os.listdir(WORKSPACE_DIR):
        if file.endswith("_segments.json"):
            base_name = file.replace("_segments.json", "")
            json_path = os.path.join(WORKSPACE_DIR, file)
            video_path = os.path.join(WORKSPACE_DIR, f"{base_name}.mp4")
            
            if os.path.exists(video_path):
                with open(json_path, 'r') as f:
                    data = json.load(f)
                projects.append({
                    "video_name": f"{base_name}.mp4",
                    "video_path": video_path,
                    "json_path": json_path,
                    "data": data,
                    "clips": sum(len(short.get("phases", [])) for short in data.get("shorts", []))
                })
    return {"status": "success", "projects": projects}

@app.post("/api/generate-short")
async def generate_short(background_tasks: BackgroundTasks):
    logger.info("Received request to generate a new short from factory buckets.")
    
    # Find any project directory in outputs
    proj_dirs = [os.path.join(OUTPUTS_DIR, d) for d in os.listdir(OUTPUTS_DIR) if os.path.isdir(os.path.join(OUTPUTS_DIR, d)) and d not in ["Proposition", "Struggle", "Result"]]
    
    if not proj_dirs:
        raise HTTPException(status_code=400, detail="No sliced projects found.")
        
    proj_dir = random.choice(proj_dirs)
    video_id = os.path.basename(proj_dir)
    
    # Group clips by variant_id
    # Format: {video_id}_{variant_id}_{phase_idx}_{phase_id}.mp4
    variants = {}
    for f in os.listdir(proj_dir):
        if f.endswith('.mp4'):
            parts = f.replace('.mp4', '').split('_')
            # Handle variable length splits, assume variant_id is parts[1] (if parts[0] is video_id without underscores)
            # Actually, simpler: we know they belong to the same variant if they share the same prefix up to the index.
            # Let's just find all unique variants from the segments JSON
            pass
            
    # Safest fallback for the API without changing frontend: find the segments.json
    segments_path = os.path.join(WORKSPACE_DIR, f"{video_id}_segments.json")
    if not os.path.exists(segments_path):
        raise HTTPException(status_code=400, detail="JSON blueprint not found.")
        
    with open(segments_path, 'r') as f:
        data = json.load(f)
        
    shorts = data.get("shorts", [])
    if not shorts:
        raise HTTPException(status_code=400, detail="No variants available.")
        
    short = random.choice(shorts)
    variant_id = short.get("variant_id", "default")
    
    clips = []
    for idx, phase in enumerate(short.get("phases", [])):
        phase_id = phase.get('phase_id', f"phase_{idx}")
        clip_path = os.path.join(proj_dir, f"{video_id}_{variant_id}_{idx}_{phase_id}.mp4")
        if os.path.exists(clip_path):
            clips.append(clip_path)
            
    if len(clips) != len(short.get("phases", [])):
        raise HTTPException(status_code=400, detail="Not all clips for this variant are generated yet.")
        
    out_file = os.path.join(OUTPUTS_DIR, f"viral_short_{video_id}_{variant_id}.mp4")
    
    clips_data = {"clips": clips}
    
    logger.info(f"Stage 3: Pipeline Editor starting for {variant_id}")
    background_tasks.add_task(execute_pipeline, clips_data, out_file)
    
    return {"status": "success", "message": "Rendering started", "video_id": f"{video_id}_{variant_id}"}

@app.get("/api/factory-status")
async def get_factory_status():
    clip_count = 0
    if os.path.exists(OUTPUTS_DIR):
        for root, _, files in os.walk(OUTPUTS_DIR):
            for file in files:
                if file.endswith('.mp4') and not file.startswith('viral_short_'):
                    clip_count += 1
    
    return {"status": "success", "counts": {"total_dynamic_clips": clip_count}}

@app.post("/api/sfx/install")
async def install_sfx():
    logger.info("Starting SFX pack synthesis...")
    results = {}
    
    sfx_manifest = {
        "impact.mp3": ["ffmpeg", "-y", "-f", "lavfi", "-i", "aevalsrc='sin(400*exp(-t*4)*t)*exp(-t*2)':d=1", "-af", "volume=5"],
        "riser.mp3": ["ffmpeg", "-y", "-f", "lavfi", "-i", "aevalsrc='sin(100*t*t*t)':d=2", "-af", "volume=2"],
        "whoosh.mp3": ["ffmpeg", "-y", "-f", "lavfi", "-i", "anoisesrc=c=pink:d=1.5", "-af", "aeval='val*sin(t*3)*exp(-t*3)',volume=5"]
    }
    
    for filename, cmd_base in sfx_manifest.items():
        filepath = os.path.join(SFX_DIR, filename)
        if not os.path.exists(filepath):
            try:
                cmd = cmd_base + [filepath]
                subprocess.run(cmd, check=True, capture_output=True)
                results[filename] = "synthesized"
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to synthesize {filename}: {e.stderr.decode()}")
                results[filename] = f"error: {str(e)}"
        else:
            results[filename] = "already exists"
            
    return {"status": "success", "results": results}

from fastapi.responses import FileResponse

@app.get("/api/videos")
async def list_videos():
    try:
        videos = []
        if os.path.exists(OUTPUTS_DIR):
            for file in os.listdir(OUTPUTS_DIR):
                if file.startswith("viral_short_") and file.endswith(".mp4"):
                    videos.append({
                        "id": file.replace("viral_short_", "").replace(".mp4", ""),
                        "filename": file
                    })
        return {"status": "success", "videos": videos}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/download/{video_id}")
async def download_video(video_id: str):
    filename = f"viral_short_{video_id}.mp4"
    path = os.path.join(OUTPUTS_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Video not found")
    return FileResponse(path, media_type="video/mp4", filename=filename)
