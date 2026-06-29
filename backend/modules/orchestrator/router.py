from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from core.service_registry import get_service
from modules.orchestrator.service import orchestrator_service
from modules.orchestrator.manager import AIOrchestratorStateMachine
from core.file_manager import file_manager
import logging
import uuid
import json

logger = logging.getLogger(__name__)
router = APIRouter()

editor_service = get_service("editor")

class AnalyzeRequest(BaseModel):
    video_id: str
    metadata: dict = {}

def run_orchestrator_job(job_id: str, video_path: str, metadata: dict, resume_state: dict = None):
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
        output_json = orchestrator.orchestrate_pipeline(job_id, resume_state=resume_state)

        from pathlib import Path
        base_name = Path(video_path).stem
        file_manager.write_json("base_asset", f"{base_name}_segments.json", output_json)
        
        output_path = file_manager.get_absolute_path("base_asset", f"{base_name}_segments.json")
        job_logger.info(f"AI Analysis Complete! Saved categorization to {output_path}")
        orchestrator_service.update_job_status(job_id, "completed", json_path=output_path)

    except Exception as e:
        import traceback
        traceback.print_exc()
        job_logger.error(f"Error in background task: {e}")
        orchestrator_service.update_job_status(job_id, f"failed: {str(e)}")
        orchestrator_service.fail_running_stages(job_id)

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
            try:
                data = file_manager.read_text("agent_output", f"{job_id}/chunk_{chunk_id}_{stage_name}.json")
                resume_state[chunk_id][stage_name] = data
            except Exception:
                pass

    orchestrator_service.update_job_status(job_id, "processing")
    background_tasks.add_task(
        run_orchestrator_job,
        job_id=job_id,
        video_path=job["video_path"],
        metadata=json.loads(job["metadata"]) if job["metadata"] else {},
        resume_state=resume_state,
    )
    return {"status": "success", "message": "Redrive initiated", "job_id": job_id}
