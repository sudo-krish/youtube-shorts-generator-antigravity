import os
import json
from pathlib import Path

# Base Directory Paths
BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"

# Specialized Asset Directories
MODELS_DIR = ASSETS_DIR / "models"
AUDIO_ASSETS_DIR = ASSETS_DIR / "audio_assets"
OUTPUT_DIR = ASSETS_DIR / "output"
VIDEOS_DIR = ASSETS_DIR / "videos"
TMP_DIR = ASSETS_DIR / "tmp"

# Chunk Directories
CHUNKS_DIR = ASSETS_DIR / "chunks"
VIDEO_CHUNKS_DIR = CHUNKS_DIR / "video_chunks"
AUDIO_CHUNKS_DIR = CHUNKS_DIR / "audio_chunks"

# Ensure directories exist
for _dir in [MODELS_DIR, AUDIO_ASSETS_DIR, OUTPUT_DIR, VIDEOS_DIR, TMP_DIR, CHUNKS_DIR, VIDEO_CHUNKS_DIR, AUDIO_CHUNKS_DIR]:
    _dir.mkdir(parents=True, exist_ok=True)

def get_asset_path(filename: str, asset_type: str) -> str:
    """Helper to resolve paths based on asset type."""
    directories = {
        "model": MODELS_DIR,
        "audio": AUDIO_ASSETS_DIR,
        "output": OUTPUT_DIR,
        "video": VIDEOS_DIR,
        "tmp": TMP_DIR,
        "video_chunk": VIDEO_CHUNKS_DIR,
        "audio_chunk": AUDIO_CHUNKS_DIR
    }
    return str(directories.get(asset_type, ASSETS_DIR) / filename)

# Load configuration (like LLM models) from config.json or fallback
CONFIG_PATH = BASE_DIR / "config.json"
if CONFIG_PATH.exists():
    with open(CONFIG_PATH, "r") as f:
        APP_CONFIG = json.load(f)
else:
    APP_CONFIG = {
        "models": {
            "observer": "deepseek-v4-flash",
            "scriptwriter": "deepseek-v4-flash",
            "director": "deepseek-v4-flash",
            "editor": "deepseek-v4-pro",
            "specialist": "deepseek-v4-pro",
            "builder": "deepseek-v4-flash"
        }
    }

def get_llm_model(agent_name: str) -> str:
    return APP_CONFIG.get("models", {}).get(agent_name, "deepseek-v4-flash")
