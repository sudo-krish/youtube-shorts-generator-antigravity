from fastapi import APIRouter, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Dict, Any, List
from modules.orchestrator.service import orchestrator_service
from core.service_registry import get_service
editor_service = get_service("editor")
from modules.orchestrator.manager import AIOrchestratorStateMachine
import asyncio
from core.file_manager import file_manager
from pathlib import Path
import logging
import uuid
import asyncio
import json

logger = logging.getLogger(__name__)

router = APIRouter()


class AnalyzeRequest(BaseModel):
    video_id: str
    metadata: dict = {}

class BatchRenderRequest(BaseModel):
    variants: List[int]

def run_orchestrator_job(job_id: str, video_path: str, metadata: dict, resume_state: dict = None):
    job_logger = logging.getLogger("ai_director")
    log_dir = os.path.join(OUTPUTS_DIR, "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, f"{job_id}.log")

    if not any(isinstance(h, logging.FileHandler) and h.baseFilename == os.path.abspath(log_path) for h in job_logger.handlers):
        fh = logging.FileHandler(log_path)
        fh.setFormatter(logging.Formatter("%(asctime)s | [%(levelname)s] | %(message)s"))
        job_logger.addHandler(fh)
        job_logger.setLevel(logging.INFO)

    try:
        job_logger.info(f"Starting orchestrator for job {job_id} on video {video_path}")
        orchestrator = AIOrchestratorStateMachine(video_path=video_path, metadata=metadata)
        output_json = orchestrator.orchestrate_pipeline(job_id, resume_state=resume_state)

        base_name = os.path.splitext(os.path.basename(video_path))[0]
        output_path = os.path.join(ASSETS_DIR, f"{base_name}_segments.json")
        with open(output_path, "w") as f:
            json.dump(output_json, f, indent=2)

        job_logger.info(f"AI Analysis Complete! Saved categorization to {output_path}")
        orchestrator_service.update_job_status(job_id, "completed", json_path=output_path)

    except Exception as e:
        import traceback
        traceback.print_exc()
        job_logger.error(f"Error in background task: {e}")
        orchestrator_service.update_job_status(job_id, f"failed: {str(e)}")
        orchestrator_service.fail_running_stages(job_id)


@router.websocket("/jobs/{job_id}/logs/stream")
async def websocket_logs(websocket: WebSocket, job_id: str):
    await websocket.accept()
    log_path = os.path.join(OUTPUTS_DIR, "logs", f"{job_id}.log")

    try:
        while not os.path.exists(log_path):
            await asyncio.sleep(0.5)

        with open(log_path, "r") as f:
            initial_content = f.read()
            if initial_content:
                await websocket.send_text(initial_content)

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

@router.post("/analyze")
async def start_analysis(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    logger.info(f"Starting async AI analysis on video {request.video_id} with metadata {request.metadata}...")

    video_record = editor_service.get_video(request.video_id)
    if not video_record:
        raise HTTPException(status_code=404, detail="Video not found")

    job_id = str(uuid.uuid4())
    orchestrator_service.create_job(job_id, request.video_id, request.metadata)

    background_tasks.add_task(
        run_orchestrator_job,
        job_id=job_id,
        video_path=video_record["video_path"],
        metadata=request.metadata,
    )
    return {"status": "success", "job_id": job_id}

@router.post("/redrive/{job_id}")
async def redrive_job(job_id: str, background_tasks: BackgroundTasks):
    job = orchestrator_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    orchestrator_service.fail_running_stages(job_id)

    completed_stages = orchestrator_service.get_completed_stages(job_id)


    resume_state = {}
    for stage in completed_stages:
        stage_name = stage["stage_name"]
        chunk_id = stage.get("chunk_id")
        if chunk_id is not None:
            if chunk_id not in resume_state:
                resume_state[chunk_id] = {}
            stage_file = os.path.join(agents_dir, f"chunk_{chunk_id}_{stage_name}.json")
            if os.path.exists(stage_file):
                with open(stage_file, "r") as f:
                    f.seek(0)
                    resume_state[chunk_id][stage_name] = f.read()

    orchestrator_service.update_job_status(job_id, "processing")
    background_tasks.add_task(
        run_orchestrator_job,
        job_id=job_id,
        video_path=job["video_path"],
        metadata=json.loads(job["metadata"]) if job["metadata"] else {},
        resume_state=resume_state,
    )
    return {"status": "success", "message": "Redrive initiated", "job_id": job_id}

@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    logger.info(f"User requested cancellation of job {job_id}")
    job = orchestrator_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    orchestrator_service.update_job_status(job_id, "failed: cancelled by user")
    orchestrator_service.fail_running_stages(job_id)
    return {"status": "success", "message": "Job cancelled"}

@router.get("/jobs")
async def list_jobs_endpoint():
    return {"status": "success", "jobs": orchestrator_service.get_all_jobs()}

@router.get("/jobs/{job_id}/stages")
async def get_job_stages_endpoint(job_id: str):
    return {"status": "success", "stages": orchestrator_service.get_stages(job_id)}

@router.get("/jobs/{job_id}/nodes/{node_id}")
async def get_node_result(job_id: str, node_id: str):
    agents_dir = os.path.join(OUTPUTS_DIR, "agents", job_id)
    for filename in os.listdir(agents_dir):
        if filename.endswith(f"_{node_id}.json"):
            with open(os.path.join(agents_dir, filename), "r") as f:
                try:
                    return {"status": "success", "data": json.load(f)}
                except json.JSONDecodeError:
                    f.seek(0)
                    return {"status": "success", "data": f.read()}
    raise HTTPException(status_code=404, detail="Node artifact not found")

@router.get("/jobs/{job_id}/status")
async def get_status(job_id: str):
    job = orchestrator_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    stages = orchestrator_service.get_stages(job_id)
    return {"status": job["status"], "stages": stages}

@router.get("/jobs/{job_id}/logs")
async def get_logs(job_id: str):
    log_path = os.path.join(OUTPUTS_DIR, "logs", f"{job_id}.log")
    if not os.path.exists(log_path):
        return {"status": "success", "logs": ""}
    with open(log_path, "r") as f:
        return {"status": "success", "logs": f.read()}

@router.post("/jobs/{job_id}/render/batch")
async def render_batch(job_id: str, request: BatchRenderRequest):
    from core.queue import render_queue
    job = orchestrator_service.get_job(job_id)
    if not job or not job.get("json_path"):
        raise HTTPException(status_code=404, detail="Job blueprint not found")

    for variant_id in request.variants:
        task_id = str(uuid.uuid4())
        orchestrator_service.queue_render(task_id, job_id, variant_id)

        # Asyncio background tasks won't easily block like threads so we use the global queue
        # For a clean router, queueing to a global variable is typical FastAPI
        # Make sure render_queue is exposed somewhere
        import asyncio
        loop = asyncio.get_event_loop()
        loop.create_task(render_queue.put({"job_id": job_id, "variant_id": variant_id, "task_id": task_id}))

    return {"status": "success", "message": f"Queued {len(request.variants)} variants."}

@router.get("/renders/{job_id}")
async def get_renders_endpoint(job_id: str):
    return {"renders": orchestrator_service.get_renders(job_id)}

@router.get("/factory-status")
async def get_factory_status():
    from core.queue import render_queue
    return {"status": "success", "queue_size": render_queue.qsize()}
