import os
from pathlib import Path

backend_dir = Path("backend/modules")

# Create directories
dirs = ["jobs", "analyze", "redrive", "renders", "factory_status", "upload", "videos", "games", "metrics", "config", "models", "db", "sfx", "test"]
for d in dirs:
    (backend_dir / d).mkdir(parents=True, exist_ok=True)
    (backend_dir / d / "__init__.py").touch()

# 1. JOBS MODULE
jobs_router = """from fastapi import APIRouter, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import List
from modules.orchestrator.service import orchestrator_service
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
    return {"status": "success", "jobs": orchestrator_service.get_all_jobs()}

@router.get("/{job_id}/status")
async def get_status(job_id: str):
    job = orchestrator_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    stages = orchestrator_service.get_stages(job_id)
    return {"status": job["status"], "stages": stages}

@router.get("/{job_id}/stages")
async def get_job_stages_endpoint(job_id: str):
    return {"status": "success", "stages": orchestrator_service.get_stages(job_id)}

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
    job = orchestrator_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    orchestrator_service.update_job_status(job_id, "failed: cancelled by user")
    orchestrator_service.fail_running_stages(job_id)
    return {"status": "success", "message": "Job cancelled"}

@router.post("/{job_id}/render/batch")
async def render_batch(job_id: str, request: BatchRenderRequest):
    from core.queue import render_queue
    job = orchestrator_service.get_job(job_id)
    if not job or not job.get("json_path"):
        raise HTTPException(status_code=404, detail="Job blueprint not found")
    for variant_id in request.variants:
        task_id = str(uuid.uuid4())
        orchestrator_service.queue_render(task_id, job_id, variant_id)
        loop = asyncio.get_event_loop()
        loop.create_task(render_queue.put({"job_id": job_id, "variant_id": variant_id, "task_id": task_id}))
    return {"status": "success", "message": f"Queued {len(request.variants)} variants."}
"""
(backend_dir / "jobs" / "router.py").write_text(jobs_router)


# 2. ANALYZE MODULE
analyze_router = """from fastapi import APIRouter, HTTPException, BackgroundTasks
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

@router.post("")
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
"""
(backend_dir / "analyze" / "router.py").write_text(analyze_router)


# 3. REDRIVE MODULE
redrive_router = """from fastapi import APIRouter, HTTPException, BackgroundTasks
from modules.orchestrator.service import orchestrator_service
from core.file_manager import file_manager
import logging
import json
from modules.analyze.router import run_orchestrator_job

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/{job_id}")
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
"""
(backend_dir / "redrive" / "router.py").write_text(redrive_router)

# 4. RENDERS MODULE
renders_router = """from fastapi import APIRouter
from modules.orchestrator.service import orchestrator_service

router = APIRouter()

@router.get("/{job_id}")
async def get_renders_endpoint(job_id: str):
    return {"renders": orchestrator_service.get_renders(job_id)}
"""
(backend_dir / "renders" / "router.py").write_text(renders_router)


# 5. FACTORY STATUS MODULE
factory_router = """from fastapi import APIRouter

router = APIRouter()

@router.get("")
async def get_factory_status():
    from core.queue import render_queue
    return {"status": "success", "queue_size": render_queue.qsize()}
"""
(backend_dir / "factory_status" / "router.py").write_text(factory_router)


# 6. STUB MODULES
stub_content = """from fastapi import APIRouter

router = APIRouter()

@router.get("")
async def stub_get():
    return {"status": "success", "data": "Not yet fully implemented."}

@router.post("")
async def stub_post():
    return {"status": "success", "data": "Not yet fully implemented."}
"""

stubs = ["upload", "videos", "games", "metrics", "config", "models", "db", "sfx"]
for stub in stubs:
    (backend_dir / stub / "router.py").write_text(stub_content)


# 7. TEST / PLAYGROUND MODULE
test_router = """from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import importlib
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class RunAgentRequest(BaseModel):
    agent: str
    payload: dict

@router.get("/agents")
async def list_agents():
    # Return available agent names
    agents = ["scriptwriter", "narrator", "director", "editor", "builder", "specialist"]
    return {"status": "success", "agents": agents}

@router.post("/run")
async def run_agent(request: RunAgentRequest):
    agent_name = request.agent.lower()
    module_name = f"modules.ai.agents.roles.{agent_name}"
    
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError:
        raise HTTPException(status_code=404, detail=f"Agent module {module_name} not found")
        
    agent_class = None
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if hasattr(attr, "__bases__"):
            from modules.ai.agents import BaseDynamicAgent
            if issubclass(attr, BaseDynamicAgent) and attr is not BaseDynamicAgent:
                agent_class = attr
                break
                
    if not agent_class:
        raise HTTPException(status_code=404, detail=f"Agent class not found in {module_name}")
        
    try:
        instance = agent_class()
        result = instance.execute(request.payload)
        return {"status": "success", "output": result}
    except Exception as e:
        logger.error(f"Error running agent {agent_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/transformers")
async def test_transformers_stub():
    return {"status": "success", "data": "Replaced by Test API Playground"}

@router.post("/transformers/run")
async def run_transformers_stub():
    return {"status": "success", "data": "Replaced by Test API Playground"}
"""
(backend_dir / "test" / "router.py").write_text(test_router)

# 8. REMOVE LEGACY ORCHESTRATOR ROUTER
orch_router = backend_dir / "orchestrator" / "router.py"
if orch_router.exists():
    orch_router.unlink()

print("Script completed!")
