from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
from core.db.manager import db
from app.orchestrator.config_manager import get_config, set_config
import os
import logging
import urllib.request
import zipfile

logger = logging.getLogger(__name__)

router = APIRouter()

ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets")
OUTPUTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "outputs")
SFX_DIR = os.path.join(ASSETS_DIR, "sfx")
os.makedirs(SFX_DIR, exist_ok=True)


class ConfigUpdate(BaseModel):
    category: str
    key: str
    value: Any

class GameCreate(BaseModel):
    game_name: str
    game_type_id: int

class GameContextUpdate(BaseModel):
    context: str

class SFXInstallRequest(BaseModel):
    url: str

@router.get("/config")
async def fetch_config():
    """Returns the current orchestration configuration."""
    return get_config()

@router.post("/config")
async def update_config(update: ConfigUpdate):
    """Updates a configuration value."""
    success = set_config(update.category, update.key, update.value)
    if success:
        return {"status": "success", "message": "Config updated"}
    raise HTTPException(status_code=400, detail="Invalid config key")

@router.get("/models")
async def get_models():
    """Returns the list of enabled AI models across providers."""
    # This is a stub from the original main.py, typically returning constant lists
    return {
        "status": "success",
        "models": {
            "OpenAI": ["gpt-4o", "gpt-4o-mini", "o1", "o3-mini"],
            "Anthropic": ["claude-3-7-sonnet-latest", "claude-3-5-haiku-latest"],
            "Google": ["gemini-2.5-flash", "gemini-2.5-pro"],
            "DeepSeek": ["deepseek-chat", "deepseek-reasoner"],
        },
    }

@router.get("/db/games")
async def db_get_games():
    """Returns all supported games and game types."""
    try:
        games = db.games.get_supported_games()
        types = db.games.get_game_types()
        return {"status": "success", "games": games, "types": types}
    except Exception as e:
        logger.error(f"Failed to fetch games: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/db/games")
async def db_create_game(req: GameCreate):
    """Registers a new game into the database."""
    try:
        db.games.create_game(req.game_name, req.game_type_id)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to create game: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/db/games/{game_id}/context")
async def get_game_context(game_id: int):
    """Retrieves the context text file for a specific game."""
    path = db.games.get_game_context_path(game_id)
    if not path or not os.path.exists(path):
        return {"status": "success", "context": ""}
    with open(path, "r") as f:
        return {"status": "success", "context": f.read()}

@router.post("/db/games/{game_id}/context")
async def update_game_context(game_id: int, update: GameContextUpdate):
    """Updates the context text file for a specific game."""
    path = db.games.get_game_context_path(game_id)
    if not path:
        return {"status": "error", "message": "Game not found"}
    with open(path, "w") as f:
        f.write(update.context)
    return {"status": "success"}

@router.get("/db/metrics")
async def get_metrics():
    """Returns aggregate usage metrics from the database."""
    return {"status": "success", "data": db.models.get_metrics_summary()}

@router.get("/metrics/balance")
async def get_deepseek_balance():
    """Stubs deepseek balance fetch, returns fake data."""
    return {"status": "success", "balance": 42.50}

@router.get("/db/dump")
async def db_dump():
    """Dumps the entire SQLite database into JSON."""
    return db.get_database_dump()

@router.delete("/db/clear")
async def clear_db():
    """Wipes the database and clears the agents directory."""
    logger.warning("Clearing database and workspace files!")
    db.clear_all()

    import shutil
    agents_dir = os.path.join(OUTPUTS_DIR, "agents")
    if os.path.exists(agents_dir):
        shutil.rmtree(agents_dir)
    os.makedirs(agents_dir, exist_ok=True)

    return {"status": "success", "message": "Database and outputs cleared."}

@router.post("/sfx/install")
async def install_sfx(request: SFXInstallRequest):
    """Downloads and extracts an SFX zip pack into the SFX directory."""
    try:
        zip_path = os.path.join(SFX_DIR, "temp_sfx.zip")
        urllib.request.urlretrieve(request.url, zip_path)
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(SFX_DIR)
        os.remove(zip_path)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to install SFX: {e}")
        raise HTTPException(status_code=500, detail=str(e))
