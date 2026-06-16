from fastapi import APIRouter

from app.transformers.router import router as transformers_router
from app.agents.router import router as agents_router
from app.generator.router import router as generator_router
from app.testing.router import router as testing_router
from app.upload.router import router as upload_router
from app.admin.router import router as admin_router
from app.orchestrator.router import router as orchestrator_router

api_router = APIRouter()

api_router.include_router(transformers_router, prefix="/transformers", tags=["transformers"])
api_router.include_router(agents_router, prefix="/agents", tags=["agents"])
api_router.include_router(generator_router, tags=["generator"]) # we omit prefix for backward compatibility if needed, or put prefix. The endpoints are currently root level (/api/splice).
api_router.include_router(testing_router, prefix="/testing", tags=["testing"])
api_router.include_router(upload_router, tags=["upload"])
api_router.include_router(admin_router, tags=["admin"])
api_router.include_router(orchestrator_router, tags=["orchestrator"])
