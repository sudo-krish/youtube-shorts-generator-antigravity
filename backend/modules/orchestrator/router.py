from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from core.service_registry import get_service
from modules.jobs.service import job_service
from modules.orchestrator.manager import AIOrchestratorStateMachine
from core.file_manager import file_manager
import logging
import uuid
import json

logger = logging.getLogger(__name__)
router = APIRouter()

editor_service = get_service("editor")

class SequenceStep(BaseModel):
    name: str
    endpoint: str
    params: Dict[str, Any] = {}

class RunRequest(BaseModel):
    video_id: str
    metadata: dict = {}
    sequence: Optional[List[SequenceStep]] = None

def run_orchestrator_job(job_id: str, video_path: str, metadata: dict, sequence: list = None, resume_state: dict = None):
    job_logger = logging.getLogger("ai_director")
    log_path = file_manager.get_absolute_path("logs", f"{job_id}.log")

    if not any(isinstance(h, logging.FileHandler) and h.baseFilename == log_path for h in job_logger.handlers):
        fh = logging.FileHandler(log_path)
        fh.setFormatter(logging.Formatter("%(asctime)s | [%(levelname)s] | %(message)s"))
        job_logger.addHandler(fh)
        job_logger.setLevel(logging.INFO)

    try:
        job_logger.info(f"Starting orchestrator for job {job_id} on video {video_path}")
        orchestrator = AIOrchestratorStateMachine(video_path=video_path, metadata=metadata)
        
        seq_dicts = [step.dict() for step in sequence] if sequence else None
        output_json = orchestrator.orchestrate_pipeline(job_id, resume_state=resume_state, sequence=seq_dicts)

        from pathlib import Path
        base_name = Path(video_path).stem
        file_manager.write_json("base_asset", f"{base_name}_segments.json", output_json)
        
        output_path = file_manager.get_absolute_path("base_asset", f"{base_name}_segments.json")
        job_logger.info(f"AI Analysis Complete! Saved categorization to {output_path}")
        job_service.update_job_status(job_id, "completed", json_path=output_path)

    except Exception as e:
        import traceback
        traceback.print_exc()
        job_logger.error(f"Error in background task: {e}")
        job_service.update_job_status(job_id, f"failed: {str(e)}")
        job_service.fail_running_stages(job_id)

@router.post("/redrive/{job_id}")
async def redrive_job(job_id: str, background_tasks: BackgroundTasks):
    job = job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job_service.fail_running_stages(job_id)
    completed_stages = job_service.get_completed_stages(job_id)

    resume_state = {}
    for stage in completed_stages:
        stage_name = stage["stage_name"]
        chunk_id = stage.get("chunk_id")
        if chunk_id is not None:
            if chunk_id not in resume_state:
                resume_state[chunk_id] = {}
            # We don't have the full payload in the DB, just the fact it completed.
            # But the orchestrator reads the file from disk anyway if we pass the state.
            resume_state[chunk_id][stage_name] = True

    # Note: redrive currently falls back to default sequence since sequence isn't saved in DB
    background_tasks.add_task(
        run_orchestrator_job,
        job_id=job_id,
        video_path=job["video_path"],
        metadata=job.get("metadata", {}),
        sequence=None, 
        resume_state=resume_state
    )
    return {"status": "success", "message": f"Redriving job {job_id}", "job_id": job_id}

@router.post("/run")
async def start_run(request: RunRequest, background_tasks: BackgroundTasks):
    logger.info(f"Starting async AI Orchestrator run on video {request.video_id} with sequence: {request.sequence}")
    video_record = editor_service.get_video(request.video_id)
    if not video_record:
        raise HTTPException(status_code=404, detail="Video not found")
    job_id = str(uuid.uuid4())
    job_service.create_job(job_id, request.video_id, request.metadata)
    background_tasks.add_task(
        run_orchestrator_job,
        job_id=job_id,
        video_path=video_record["video_path"],
        metadata=request.metadata,
        sequence=request.sequence
    )
    return {"status": "success", "job_id": job_id}
