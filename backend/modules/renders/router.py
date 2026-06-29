from fastapi import APIRouter
from modules.orchestrator.service import orchestrator_service

router = APIRouter()

@router.get("/{job_id}")
async def get_renders_endpoint(job_id: str):
    return {"renders": orchestrator_service.get_renders(job_id)}
