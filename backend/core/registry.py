import os
import inspect
import importlib
import logging
from fastapi import APIRouter
from .schemas import GenericRequest, GenericResponse
from .base_service import BaseNanoService

logger = logging.getLogger(__name__)

def build_api_router() -> APIRouter:
    """
    Scans the 'modules' directory, discovers subclasses of BaseNanoService,
    and automatically registers them as FastAPI endpoints.
    """
    router = APIRouter()
    
    # Path to the backend root (where 'modules' lives)
    backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    modules_dir = os.path.join(backend_root, "modules")
    
    if not os.path.exists(modules_dir):
        logger.warning(f"Modules directory not found at {modules_dir}")
        return router
        
    for root, _, files in os.walk(modules_dir):
        for file in files:
            if file.endswith(".py") and file != "__init__.py":
                file_path = os.path.join(root, file)
                
                # Convert file path to python module path (e.g. modules.ai.agents.observer)
                rel_path = os.path.relpath(file_path, backend_root)
                module_name = rel_path.replace(os.path.sep, ".")[:-3]
                
                try:
                    module = importlib.import_module(module_name)
                    
                    for name, obj in inspect.getmembers(module):
                        # Register BaseNanoService classes
                        if inspect.isclass(obj) and issubclass(obj, BaseNanoService) and obj is not BaseNanoService:
                            if obj.__module__ != module_name:
                                continue
                                
                            route_path = getattr(obj, "route", None)
                            if not route_path:
                                inferred_path = rel_path.replace("modules", "").replace(".py", "").replace(os.path.sep, "/")
                                route_path = inferred_path
                            
                            if not route_path.startswith("/"):
                                route_path = "/" + route_path
                                
                            _register_endpoint(router, route_path, obj)
                            logger.info(f"Auto-Discovered Nano-Service: POST /api{route_path} -> {obj.__name__}")
                        
                        # Register APIRouter instances explicitly named 'router'
                        elif isinstance(obj, APIRouter) and name == "router":
                            # Mount this sub-router using its directory path as prefix
                            inferred_prefix = rel_path.replace("modules", "").replace("/router.py", "").replace(os.path.sep, "/")
                            if not inferred_prefix.startswith("/"):
                                inferred_prefix = "/" + inferred_prefix
                                
                            router.include_router(obj, prefix=inferred_prefix)
                            logger.info(f"Auto-Discovered Domain Router: /api{inferred_prefix} -> {module_name}")
                except Exception as e:
                    logger.error(f"Failed to auto-discover module {module_name}: {e}")
                    
    return router

def _register_endpoint(router: APIRouter, path: str, service_class):
    """Dynamically binds a class to a FastAPI router endpoint."""
    @router.post(path, response_model=GenericResponse, tags=[path.split("/")[1].capitalize()])
    async def dynamic_endpoint(req: GenericRequest):
        instance = service_class()
        
        # Support both async and sync execute() methods seamlessly
        if inspect.iscoroutinefunction(instance.execute):
            result = await instance.execute(req.payload)
        else:
            result = instance.execute(req.payload)
            
        return GenericResponse(output=result)
