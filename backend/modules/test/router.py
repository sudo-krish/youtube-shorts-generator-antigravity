from fastapi import APIRouter, HTTPException
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

