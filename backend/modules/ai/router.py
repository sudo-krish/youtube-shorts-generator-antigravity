from fastapi import APIRouter, HTTPException
import logging
import numpy as np
import threading
import uuid
import asyncio

from core.settings import get_asset_path
from modules.ai.transformers.schemas import TransformerRequest, TransformerResponse
from modules.ai.transformers.transformer import get_all_transformers
from modules.ai.agents.agents import get_all_agents


router = APIRouter(tags=["ai"])
logger = logging.getLogger(__name__)

# =========================================================================
# 1. DYNAMIC AGENT ROUTES
# =========================================================================

agents_map = get_all_agents()

for name, agent_instance in agents_map.items():
    # We must capture the current `agent_instance` in the closure
    def create_endpoint(agent=agent_instance):
        async def run_agent(payload: dict):
            return agent.execute(payload)
        return run_agent
        
    router.post(f"/agents/{name}")(create_endpoint())
    logger.info(f"Registered dynamic agent route: /agents/{name}")

# =========================================================================
# 2. STATIC TRANSFORMER ROUTES
# =========================================================================

transformers_map = get_all_transformers()

for name, TransformerClass in transformers_map.items():
    def create_transformer_endpoint(t_class=TransformerClass):
        async def run_transformer(req: TransformerRequest):
            transformer = t_class()
            payload = req.model_dump()
            return await transformer.execute(payload)
        return run_transformer

    # We skip response_model=TransformerResponse to allow transformers to return raw dicts
    router.post(f"/transformers/{name}")(create_transformer_endpoint())
    logger.info(f"Registered dynamic transformer route: /transformers/{name}")
