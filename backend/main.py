import os
import json
import asyncio
from fastapi import FastAPI, UploadFile, Request, File, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
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
from database import init_db, create_job, update_job_status, get_all_jobs, get_job_stages, get_job, create_video, get_video, get_completed_stages, get_database_dump, clear_database
import shutil

USAGE_FILE = os.path.join(OUTPUTS_DIR, "usage_tracking.json")

app = FastAPI(title="Hyper Shorts Factory API")
app.mount("/workspace", StaticFiles(directory=WORKSPACE_DIR), name="workspace")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/api/jobs/{job_id}/logs/stream")
async def websocket_logs(websocket: WebSocket, job_id: str):
    await websocket.accept()
    log_path = os.path.join(OUTPUTS_DIR, "logs", f"{job_id}.log")
    
    try:
        # Wait for file to exist
        while not os.path.exists(log_path):
            await asyncio.sleep(0.5)
            
        with open(log_path, 'r') as f:
            # Send everything available initially
            initial_content = f.read()
            if initial_content:
                await websocket.send_text(initial_content)
                
            # Tail the file asynchronously
            while True:
                line = f.read()
                if not line:
                    await asyncio.sleep(0.5)
                    continue
                await websocket.send_text(line)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error for job {job_id}: {e}")
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
    job_logger = logging.getLogger("ai_director")
    log_dir = os.path.join(OUTPUTS_DIR, "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, f"{job_id}.log")
    
    # Attach handler if not present for this job
    if not any(isinstance(h, logging.FileHandler) and h.baseFilename == os.path.abspath(log_path) for h in job_logger.handlers):
        fh = logging.FileHandler(log_path)
        fh.setFormatter(logging.Formatter('%(asctime)s | [%(levelname)s] | %(message)s'))
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
        # Also mark any stuck running stages as failed
        import sqlite3
        from database import DB_PATH
        import time
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE job_stages SET status = 'failed', end_time = ? WHERE job_id = ? AND status IN ('running', 'processing')", (time.time(), job_id))
        conn.commit()
        conn.close()

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
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    # Set all stuck running stages to failed before redriving
    import sqlite3
    import time
    from database import DB_PATH
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE job_stages SET status = 'failed', end_time = ? WHERE job_id = ? AND status IN ('running', 'processing')", (time.time(), job_id))
    conn.commit()
    conn.close()
    
    completed_stages = get_completed_stages(job_id)
    agents_dir = os.path.join(OUTPUTS_DIR, "agents", job_id)
    os.makedirs(agents_dir, exist_ok=True)
    
    # We reconstruct a resume_state dictionary from the DB
    resume_state = {}
    for stage in completed_stages:
        chunk_id = stage['chunk_id']
        stage_name = stage['stage_name']
        
        if chunk_id is None:
            continue
            
        if chunk_id not in resume_state:
            resume_state[chunk_id] = {}
            
        file_path = os.path.join(agents_dir, str(chunk_id), f"{stage_name}.txt")
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                try:
                    import json
                    resume_state[chunk_id][stage_name] = json.load(f)
                except Exception:
                    f.seek(0)
                    resume_state[chunk_id][stage_name] = f.read()
    
    update_job_status(job_id, "processing")
    
    background_tasks.add_task(
        run_orchestrator_job,
        job_id=job_id,
        video_path=job["video_path"],
        metadata=job.get("metadata", {}),
        resume_state=resume_state
    )
    
    return {"job_id": job_id, "status": "processing", "message": "Redrive initiated"}

@app.post("/api/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    logger.info(f"User requested cancellation of job {job_id}")
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    update_job_status(job_id, "failed: cancelled by user")
    
    import sqlite3
    import time
    from database import DB_PATH
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE job_stages SET status = 'failed', end_time = ? WHERE job_id = ? AND status IN ('running', 'processing')", (time.time(), job_id))
    conn.commit()
    conn.close()
    
    return {"status": "success", "message": "Job marked as failed."}

@app.get("/api/jobs")
async def list_jobs_endpoint():
    return {"status": "success", "jobs": get_all_jobs()}

@app.get("/api/jobs/{job_id}/stages")
async def list_job_stages_endpoint(job_id: str):
    return {"status": "success", "stages": get_job_stages(job_id)}

@app.get("/api/jobs/{job_id}/nodes/{node_id}")
async def get_node_output(job_id: str, node_id: str):
    # node_id format is typically "chunk_{chunk_id}_{stage_name}" or just "{stage_name}"
    chunk_id = None
    stage_name = node_id
    
    if node_id.startswith("chunk_"):
        parts = node_id.split("_")
        if len(parts) >= 3:
            chunk_id = parts[1]
            stage_name = "_".join(parts[2:])
            
    # Load from file system since outputs are too large for the sqlite database
    if chunk_id:
        file_path = os.path.join(OUTPUTS_DIR, "agents", job_id, str(chunk_id), f"{stage_name}.txt")
    else:
        file_path = os.path.join(OUTPUTS_DIR, "agents", job_id, f"{stage_name}.txt")
        
    if not os.path.exists(file_path):
        return {"status": "success", "output": "Output not generated yet."}
        
    with open(file_path, "r") as f:
        content = f.read()
        try:
            return {"status": "success", "output": json.loads(content)}
        except Exception:
            return {"status": "success", "output": content}

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
        "num_chunks": job.get("num_chunks", 0),
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

@app.get("/api/db/dump")
async def db_dump():
    return get_database_dump()

@app.delete("/api/db/clear")
async def db_clear():
    logger.warning("Clearing database and workspace files!")
    clear_database()
    
    # Safely clear outputs/agents
    agents_dir = os.path.join(OUTPUTS_DIR, "agents")
    if os.path.exists(agents_dir):
        for item in os.listdir(agents_dir):
            item_path = os.path.join(agents_dir, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
                
    # Safely clear workspace files (except sfx folder)
    if os.path.exists(WORKSPACE_DIR):
        for item in os.listdir(WORKSPACE_DIR):
            if item == "sfx":
                continue
            item_path = os.path.join(WORKSPACE_DIR, item)
            if os.path.isfile(item_path):
                os.remove(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
                
    return {"status": "success", "message": "Database and temporary files cleared"}

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

render_queue = asyncio.Queue()

async def render_worker():
    while True:
        try:
            task = await render_queue.get()
            job_id = task['job_id']
            variant_id = task['variant_id']
            task_id = task['task_id']
            job = get_job(job_id)
            if not job:
                update_render_status(task_id, 'failed', 'Job not found')
                render_queue.task_done()
                continue
                
            segments_path = job["json_path"]
            with open(segments_path, 'r') as f:
                data = json.load(f)
                
            shorts = data.get("shorts", [])
            short = next((s for s in shorts if str(s.get("variant_id")) == variant_id), None)
            
            if not short:
                update_render_status(task_id, 'failed', 'Variant not found')
                render_queue.task_done()
                continue
                
            update_render_status(task_id, 'rendering')
            
            # Step 1: Cut the clips synchronously
            filtered_data = data.copy()
            filtered_data["shorts"] = [short]
            
            try:
                generate_files_from_json(job["video_path"], filtered_data)
            except Exception as e:
                logger.error(f"Error in generate_files_from_json: {e}")
                update_render_status(task_id, 'failed', str(e))
                render_queue.task_done()
                continue
            
            # Step 2: Pipeline Editor
            vid = job["video_id"]
            v_id = short.get("variant_id", "default")
            
            variant_clips = []
            for idx, phase in enumerate(short.get("phases", [])):
                phase_id = phase.get('phase_id', f"phase_{idx}")
                clip_path = os.path.join(OUTPUTS_DIR, vid, f"{vid}_{v_id}_{idx}_{phase_id}.mp4")
                if os.path.exists(clip_path):
                    variant_clips.append(clip_path)
                    
            if len(variant_clips) == len(short.get("phases", [])):
                clips_data = {"clips": variant_clips}
                out_file = os.path.join(OUTPUTS_DIR, f"viral_short_{job_id}_{variant_id}.mp4")
                try:
                    execute_pipeline(clips_data, out_file)
                    update_render_status(task_id, 'completed')
                except Exception as e:
                    logger.error(f"Error in execute_pipeline: {e}")
                    update_render_status(task_id, 'failed', str(e))
            else:
                update_render_status(task_id, 'failed', 'Missing clips')
                
        except Exception as e:
            logger.error(f"Render worker error: {e}")
        finally:
            render_queue.task_done()

@app.on_event("startup")
async def startup_event():
    # Initialize database correctly before worker starts
    init_db()
    asyncio.create_task(render_worker())

class BatchRenderRequest(BaseModel):
    variants: List[str]

@app.post("/api/jobs/{job_id}/render/batch")
async def render_batch(job_id: str, request: BatchRenderRequest):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    for variant_id in request.variants:
        task_id = f"{job_id}_{variant_id}"
        from database import queue_render_task
        queue_render_task(task_id, job_id, variant_id)
        
        await render_queue.put({
            'job_id': job_id,
            'variant_id': variant_id,
            'task_id': task_id
        })
        
    return {"status": "success", "message": f"Queued {len(request.variants)} variants."}

@app.get("/api/jobs/{job_id}/render/status")
async def get_render_status(job_id: str):
    from database import get_render_statuses
    statuses = get_render_statuses(job_id)
    return {"status": "success", "variants": statuses}

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
