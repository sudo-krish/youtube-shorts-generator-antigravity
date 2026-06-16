from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any, List
import logging
from app.generator.cutter import generate_files_from_json
from app.generator.engine import execute_pipeline
from app.generator.tree_generator import generate_asset_tree
from app.generator.schemas import CutterRequest, RenderRequest, RenderTreeRequest

router = APIRouter(prefix="/api/generator", tags=["generator"])
logger = logging.getLogger(__name__)

class GenericResponse(BaseModel):
    status: str
    output: Any

@router.post("/cut", response_model=GenericResponse)
async def run_cutter(req: CutterRequest):
    logger.info(f"API: Running FFmpeg Cutter on {req.video_path}")
    files = generate_files_from_json(req.video_path, req.timeline_json)
    return GenericResponse(status="success", output=files)

@router.post("/render", response_model=GenericResponse)
async def run_render(req: RenderRequest):
    logger.info(f"API: Running FFmpeg Render Pipeline for {req.output_path}")
    execute_pipeline(req.clips_data, req.output_path)
    return GenericResponse(status="success", output=req.output_path)

@router.post("/render_tree", response_model=GenericResponse)
async def run_render_tree(req: RenderTreeRequest):
    logger.info(f"API: Running Multi-Hook Tree Render for Job {req.job_id}")
    # Treating output_dir as base_output_path for generate_asset_tree
    result_paths = generate_asset_tree(req.blueprint, req.output_dir)
    return GenericResponse(status="success", output=result_paths)


class SpliceRequest(BaseModel):
    video_path: str
    json_path: str

@router.post("/splice")
async def splice_video(request: SpliceRequest, background_tasks: __import__('fastapi').BackgroundTasks):
    logger.info(f"Received splice request for {request.video_path}")
    import os
    import json
    if not os.path.exists(request.video_path) or not os.path.exists(request.json_path):
        logger.error("Files not found for splice")
        raise __import__('fastapi').HTTPException(status_code=404, detail="Files not found")

    logger.info("Stage 2: File Generator starting...")
    with open(request.json_path, "r") as f:
        data = json.load(f)

    background_tasks.add_task(generate_files_from_json, request.video_path, data)
    return {"status": "success", "message": "Splicing started in background!"}


@router.get("/projects")
async def list_projects():
    import os
    import json
    projects = []
    WORKSPACE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "workspace")
    for file in os.listdir(WORKSPACE_DIR):
        if file.endswith("_segments.json"):
            base_name = file.replace("_segments.json", "")
            json_path = os.path.join(WORKSPACE_DIR, file)
            video_path = os.path.join(WORKSPACE_DIR, f"{base_name}.mp4")

            if os.path.exists(video_path):
                with open(json_path, "r") as f:
                    data = json.load(f)
                projects.append(
                    {
                        "video_name": f"{base_name}.mp4",
                        "video_path": video_path,
                        "json_path": json_path,
                        "data": data,
                        "clips": sum(
                            len(short.get("phases", []))
                            for short in data.get("shorts", [])
                        ),
                    }
                )
    return {"status": "success", "projects": projects}


@router.post("/generate-short")
async def generate_short(background_tasks: __import__('fastapi').BackgroundTasks):
    import os
    import json
    import random
    logger.info("Received request to generate a new short from factory buckets.")
    OUTPUTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "outputs")
    WORKSPACE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "workspace")

    proj_dirs = [
        os.path.join(OUTPUTS_DIR, d)
        for d in os.listdir(OUTPUTS_DIR)
        if os.path.isdir(os.path.join(OUTPUTS_DIR, d))
        and d not in ["Proposition", "Struggle", "Result"]
    ]

    if not proj_dirs:
        raise __import__('fastapi').HTTPException(status_code=400, detail="No sliced projects found.")

    proj_dir = random.choice(proj_dirs)
    video_id = os.path.basename(proj_dir)

    segments_path = os.path.join(WORKSPACE_DIR, f"{video_id}_segments.json")
    if not os.path.exists(segments_path):
        raise __import__('fastapi').HTTPException(status_code=400, detail="JSON blueprint not found.")

    with open(segments_path, "r") as f:
        data = json.load(f)

    shorts = data.get("shorts", [])
    if not shorts:
        raise __import__('fastapi').HTTPException(status_code=400, detail="No variants available.")

    short = random.choice(shorts)
    variant_id = short.get("variant_id", "default")

    clips = []
    for idx, phase in enumerate(short.get("phases", [])):
        phase_id = phase.get("phase_id", f"phase_{idx}")
        clip_path = os.path.join(
            proj_dir, f"{video_id}_{variant_id}_{idx}_{phase_id}.mp4"
        )
        if os.path.exists(clip_path):
            clips.append(clip_path)

    if len(clips) != len(short.get("phases", [])):
        raise __import__('fastapi').HTTPException(
            status_code=400, detail="Not all clips for this variant are generated yet."
        )

    out_file = os.path.join(OUTPUTS_DIR, f"viral_short_{video_id}_{variant_id}.mp4")
    clips_data = {"clips": clips}

    logger.info(f"Stage 3: Pipeline Editor starting for {variant_id}")
    background_tasks.add_task(execute_pipeline, clips_data, out_file)

    return {
        "status": "success",
        "message": "Rendering started",
        "video_id": f"{video_id}_{variant_id}",
    }
