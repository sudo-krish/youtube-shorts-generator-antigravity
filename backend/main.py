import os
import json
import asyncio
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from schemas import ViralShortsExtraction
import sys
from dotenv import load_dotenv
import urllib.request
import subprocess

load_dotenv()

import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

DOWNLOADS_DIR = os.path.join(os.path.dirname(__file__), "downloads")
SFX_DIR = os.path.join(DOWNLOADS_DIR, "sfx")
OUTPUTS_DIR = os.path.join(os.path.dirname(__file__), "outputs")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)
os.makedirs(SFX_DIR, exist_ok=True)
os.makedirs(OUTPUTS_DIR, exist_ok=True)
os.makedirs(os.path.join(OUTPUTS_DIR, "Proposition"), exist_ok=True)
os.makedirs(os.path.join(OUTPUTS_DIR, "Struggle"), exist_ok=True)
os.makedirs(os.path.join(OUTPUTS_DIR, "Result"), exist_ok=True)

from editor import render_hyper_short, assemble_random_short
from google.antigravity import Agent, LocalAgentConfig, GenerationConfig
from google.antigravity.types import from_file
from splicer_worker import slice_video_into_buckets
import random
import hashlib
import subprocess

import uuid

from orchestrator import VideoOrchestrator
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

@app.websocket("/api/logs")
async def websocket_logs(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
# -------------------------------

PROMPT = """You are an elite Valorant/FPS video editor. Your goal is to extract the top 3 to 5 Comeback Arcs from this VOD. 

=== CRITICAL NEGATIVE CONSTRAINTS (HARD ABORTS) ===
1. THE BUY PHASE RULE: If the words "BUY PHASE" or the pre-round barrier countdown are visible anywhere on screen, that footage is STRICTLY INVALID. Do not include a single frame of the Buy Phase in your Proposition.
2. THE DEATH RULE: A "Comeback" requires the player to survive and win. If the player dies, gets traded, or enters spectator mode, ABORT the extraction. It is not a comeback. 
3. THE ASSIST RULE: Do not confuse an "Assist" banner for a victory. The player MUST be the one generating the final kill in the kill-feed.

=== TACTICAL SHOOTER PACING (THE TTK RULE) ===
To achieve a 40 to 60-second total length for each fight arc, follow these padding rules:

1. Proposition (The Setup): 
   - Start 10 to 15 seconds before the engagement. 
   - CRITICAL: This setup MUST happen during the active round. It cannot include the Buy Phase. We need to see active map traversal or angle-holding.
2. Struggle (The Engagement): 
   - The player takes damage or is pushed by multiple enemies but SURVIVES.
3. Result (The Climax): 
   - The player secures the final kill. 
   - End the clip exactly 2.0 seconds after the kill.

=== TIMING & EFFECT RULES ===
- All timestamps (start_time, end_time) MUST be in absolute float seconds from the start of the raw VOD (e.g., 145.5). Do NOT use MM:SS format under any circumstances.
- Each phase must contain an array of `effects` and a list of `visual_punch_in_timestamps`.
- CRITICAL: Both effect timestamps (`relative_start_time`) and `visual_punch_in_timestamps` MUST be float seconds RELATIVE to the start of that specific phase clip (where 0.0 is the very first frame of that clip).

=== NARRATIVE TEXT STRICTNESS ===
For the `story_text`, you must strictly describe the literal action happening on screen in under 6 words. 
- BAD: "PUSHING INTO THE UNKNOWN" or "QUICK DRAW" (Too generic/cheesy).
- GOOD: "HOLDING B MAIN" or "BLINDED AND SPRAYING" or "TRADED THE REYNA".

Supported Effects Menu:
['slow_motion', 'fast_forward', 'desaturate', 'glitch', 'flashbang', 'vignette_pulse', 'screen_shake', 'zoom_punch', 'bass_boost', 'muffle_audio']

=== OUTPUT FORMAT ===
You must respond strictly in JSON format matching this schema structure:

[
  {
    "fight_number": 1,
    "proposition": {
      "start_time": 12.0,
      "end_time": 25.5,
      "visual_evidence": "Player holds angle at B main, waiting for footsteps.",
      "story_text": "THE CHASE BEGINS",
      "visual_punch_in_timestamps": [2.5, 8.0],
      "effects": [{"effect_name": "screen_shake", "relative_start_time": 2.5, "duration": 0.5}]
    },
    "struggle": {
      "start_time": 25.5,
      "end_time": 40.0,
      "visual_evidence": "Player takes heavy damage from flank, uses Devour to heal.",
      "story_text": "OUTNUMBERED OUTGUNNED",
      "visual_punch_in_timestamps": [5.2],
      "effects": [
        {"effect_name": "desaturate", "relative_start_time": 0.0, "duration": 14.5},
        {"effect_name": "vignette_pulse", "relative_start_time": 3.0, "duration": 7.0}
      ]
    },
    "result": {
      "start_time": 40.0,
      "end_time": 52.5,
      "visual_evidence": "Player hits final headshot, multi-kill feed appears.",
      "story_text": "CLEANED THEM OUT",
      "visual_punch_in_timestamps": [1.0, 11.0],
      "effects": [{"effect_name": "zoom_punch", "relative_start_time": 1.0, "duration": 1.0}]
    }
  }
]
"""

@app.post("/api/upload")
async def upload_video(file: UploadFile = File(...)):
    logger.info(f"Received upload request for {file.filename}")
    if not file.filename.endswith('.mp4'):
        logger.error(f"Invalid file type: {file.filename}")
        raise HTTPException(status_code=400, detail="Only .mp4 files are supported.")
        
    file_location = os.path.join(DOWNLOADS_DIR, file.filename)
    with open(file_location, "wb") as f:
        f.write(await file.read())
    logger.info(f"Saved file to {file_location}")
    return {"status": "success", "video_path": file_location}

class AnalyzeRequest(BaseModel):
    video_path: str

job_status = {}

def run_orchestrator_job(job_id: str, video_path: str, prompt: str):
    try:
        orchestrator = VideoOrchestrator(video_path=video_path, prompt=prompt)
        output_json = orchestrator.process_video_pipeline(job_status, job_id)
        
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        output_path = os.path.join(DOWNLOADS_DIR, f"{base_name}_segments.json")
        with open(output_path, "w") as f:
            json.dump(output_json, f, indent=2)
            
        logger.info(f"AI Analysis Complete! Saved categorization to {output_path}")
        
        if job_status and job_id in job_status:
            job_status[job_id]["json_path"] = output_path
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error(f"Error in background task: {e}")

@app.post("/api/analyze")
async def analyze_video(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    logger.info(f"Starting async AI analysis on {request.video_path}...")
    
    job_id = str(uuid.uuid4())
    job_status[job_id] = {
        "status": "processing", 
        "progress": "Initializing job...", 
        "result": None,
        "json_path": None
    }
    
    background_tasks.add_task(
        run_orchestrator_job,
        job_id=job_id,
        video_path=request.video_path,
        prompt=PROMPT
    )
    
    return {"job_id": job_id, "status": "processing"}

@app.get("/api/status/{job_id}")
async def get_status(job_id: str):
    status = job_status.get(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    return status

class SpliceRequest(BaseModel):
    video_path: str
    json_path: str

@app.post("/api/splice")
async def splice_video(request: SpliceRequest, background_tasks: BackgroundTasks):
    logger.info(f"Received splice request for {request.video_path}")
    if not os.path.exists(request.video_path) or not os.path.exists(request.json_path):
        logger.error("Files not found for splice")
        raise HTTPException(status_code=404, detail="Files not found")
        
    logger.info("Adding Splicer Worker to background tasks for splicing...")
    background_tasks.add_task(slice_video_into_buckets, request.video_path, request.json_path)
    return {"status": "success", "message": "Splicing started in background!"}

@app.get("/api/projects")
async def list_projects():
    projects = []
    for file in os.listdir(DOWNLOADS_DIR):
        if file.endswith("_segments.json"):
            base_name = file.replace("_segments.json", "")
            json_path = os.path.join(DOWNLOADS_DIR, file)
            video_path = os.path.join(DOWNLOADS_DIR, f"{base_name}.mp4")
            
            if os.path.exists(video_path):
                with open(json_path, 'r') as f:
                    data = json.load(f)
                projects.append({
                    "video_name": f"{base_name}.mp4",
                    "video_path": video_path,
                    "json_path": json_path,
                    "data": data,
                    "clips": len(data.get("propositions", [])) + len(data.get("struggles", [])) + len(data.get("results", []))
                })
    return {"status": "success", "projects": projects}

@app.post("/api/generate-short")
async def generate_short(background_tasks: BackgroundTasks):
    logger.info("Received request to generate a new short from factory buckets.")
    prop_dir = os.path.join(OUTPUTS_DIR, "Proposition")
    struggle_dir = os.path.join(OUTPUTS_DIR, "Struggle")
    result_dir = os.path.join(OUTPUTS_DIR, "Result")
    
    props = [f for f in os.listdir(prop_dir) if f.endswith('.mp4')]
    struggles = [f for f in os.listdir(struggle_dir) if f.endswith('.mp4')]
    results = [f for f in os.listdir(result_dir) if f.endswith('.mp4')]
    
    if not props or not struggles or not results:
        logger.warning("Not enough clips to generate a short.")
        raise HTTPException(status_code=400, detail="Not enough clips in all 3 buckets.")
        
    usage = {}
    if os.path.exists(USAGE_FILE):
        with open(USAGE_FILE, 'r') as f:
            usage = json.load(f)
            
    # Try to find a unique combination
    max_attempts = 1000
    for _ in range(max_attempts):
        p = random.choice(props)
        s = random.choice(struggles)
        r = random.choice(results)
        
        combo_hash = hashlib.md5(f"{p}-{s}-{r}".encode()).hexdigest()
        if combo_hash not in usage:
            # Found unique!
            usage[combo_hash] = {"prop": p, "struggle": s, "result": r}
            with open(USAGE_FILE, 'w') as f:
                json.dump(usage, f, indent=2)
                
            out_file = os.path.join(OUTPUTS_DIR, f"viral_short_{combo_hash[:8]}.mp4")
            
            p_path = os.path.join(prop_dir, p)
            s_path = os.path.join(struggle_dir, s)
            r_path = os.path.join(result_dir, r)
            
            logger.info(f"Rendering short {combo_hash[:8]} with combo: {p}, {s}, {r}")
            background_tasks.add_task(assemble_random_short, p_path, s_path, r_path, out_file)
            
            return {"status": "success", "message": "Rendering started", "video_id": combo_hash[:8]}
            
    logger.error("Exhausted all combinations!")
    raise HTTPException(status_code=400, detail="Exhausted all unique combinations.")

@app.get("/api/factory-status")
async def get_factory_status():
    prop_dir = os.path.join(OUTPUTS_DIR, "Proposition")
    struggle_dir = os.path.join(OUTPUTS_DIR, "Struggle")
    result_dir = os.path.join(OUTPUTS_DIR, "Result")
    
    props = len([f for f in os.listdir(prop_dir) if f.endswith('.mp4')]) if os.path.exists(prop_dir) else 0
    struggles = len([f for f in os.listdir(struggle_dir) if f.endswith('.mp4')]) if os.path.exists(struggle_dir) else 0
    results = len([f for f in os.listdir(result_dir) if f.endswith('.mp4')]) if os.path.exists(result_dir) else 0
    
    return {"status": "success", "counts": {"propositions": props, "struggles": struggles, "results": results}}

@app.post("/api/sfx/install")
async def install_sfx():
    logger.info("Starting SFX pack synthesis...")
    results = {}
    
    # Use FFmpeg's native lavfi synthesizer to create cinematic assets
    # This prevents 404s and avoids API keys completely!
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
