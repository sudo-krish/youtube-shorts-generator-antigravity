from fastapi import APIRouter
from modules.jobs.service import job_service

router = APIRouter()

@router.get("/{job_id}")
async def get_renders_endpoint(job_id: str):
    return {"renders": job_service.get_renders(job_id)}
