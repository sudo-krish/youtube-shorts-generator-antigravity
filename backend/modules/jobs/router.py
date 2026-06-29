from fastapi import APIRouter, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import List
from modules.jobs.service import job_service
from core.file_manager import file_manager
import asyncio
import json
import logging
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)
router = APIRouter()

class BatchRenderRequest(BaseModel):
    variants: List[int]

@router.get("")
async def list_jobs_endpoint():
    return {"status": "success", "jobs": job_service.get_all_jobs()}

@router.get("/{job_id}/status")
async def get_status(job_id: str):
    job = job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    stages = job_service.get_stages(job_id)
    return {"status": job["status"], "stages": stages}

@router.get("/{job_id}/stages")
async def get_job_stages_endpoint(job_id: str):
    return {"status": "success", "stages": job_service.get_stages(job_id)}

@router.get("/{job_id}/logs")
async def get_logs(job_id: str):
    try:
        content = file_manager.read_text("logs", f"{job_id}.log")
        return {"status": "success", "logs": content}
    except Exception:
        return {"status": "success", "logs": ""}

@router.websocket("/{job_id}/logs/stream")
async def websocket_logs(websocket: WebSocket, job_id: str):
    await websocket.accept()
    log_path = file_manager.get_absolute_path("logs", f"{job_id}.log")
    try:
        while not Path(log_path).exists():
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

@router.get("/{job_id}/nodes/{node_id}")
async def get_node_result(job_id: str, node_id: str):
    try:
        files = file_manager.list_files("agent_output", f"{job_id}/*_{node_id}.json")
        for f in files:
            try:
                data = file_manager.read_json("agent_output", f"{job_id}/{Path(f).name}")
                return {"status": "success", "data": data}
            except json.JSONDecodeError:
                content = file_manager.read_text("agent_output", f"{job_id}/{Path(f).name}")
                return {"status": "success", "data": content}
    except Exception:
        pass
    raise HTTPException(status_code=404, detail="Node artifact not found")

@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str):
    logger.info(f"User requested cancellation of job {job_id}")
    job = job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job_service.update_job_status(job_id, "failed: cancelled by user")
    job_service.fail_running_stages(job_id)
    return {"status": "success", "message": "Job cancelled"}

@router.post("/{job_id}/render/batch")
async def render_batch(job_id: str, request: BatchRenderRequest):
    from core.queue import render_queue
    job = job_service.get_job(job_id)
    if not job or not job.get("json_path"):
        raise HTTPException(status_code=404, detail="Job blueprint not found")
    for variant_id in request.variants:
        task_id = str(uuid.uuid4())
        job_service.queue_render(task_id, job_id, variant_id)
        loop = asyncio.get_event_loop()
        loop.create_task(render_queue.put({"job_id": job_id, "variant_id": variant_id, "task_id": task_id}))
    return {"status": "success", "message": f"Queued {len(request.variants)} variants."}
