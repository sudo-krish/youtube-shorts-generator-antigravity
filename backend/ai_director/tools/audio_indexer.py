import os
import json
import logging
import requests
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

# Paths
ASSETS_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets"))
MANIFEST_PATH = os.path.join(ASSETS_DIR, "asset_manifest.json")
DYNAMIC_DIR = os.path.join(ASSETS_DIR, "sfx", "dynamic")

FREESOUND_API_KEY = os.getenv("FREESOUND_API_KEY")

def score_match(query: str, tags: str) -> float:
    """Quick string similarity fallback for token matching."""
    return SequenceMatcher(None, query.lower(), tags.lower()).ratio()

def get_audio_asset(semantic_query: str) -> str:
    """
    Fetches the closest matching audio asset based on a semantic query.
    Implements a Two-Tier Strategy: Local Keyword Intersect cache -> FreeSound JIT Fetcher.
    """
    if not os.path.exists(MANIFEST_PATH):
        logger.warning("Manifest not found! Ensure download_seed_assets.py has been run.")
        return "bgm.mp3" # Fallback if system broken
        
    with open(MANIFEST_PATH, "r") as f:
        manifest = json.load(f)
        
    best_match = None
    best_score = 0.0
    
    # 1. Check local library via Keyword Intersection
    for relative_path, metadata in manifest.items():
        score = score_match(semantic_query, metadata.get("tags", ""))
        if score > best_score:
            best_score = score
            best_match = relative_path
            
    # If match is reliable, return the local file path immediately
    if best_score > 0.4:
        logger.info(f"Local asset match found for '{semantic_query}': {best_match} (score: {best_score:.2f})")
        return best_match
        
    # 2. JIT Fetch Fallback if local library lacks the asset
    if not FREESOUND_API_KEY:
        logger.warning(f"No strong local match for '{semantic_query}' and FREESOUND_API_KEY missing. Falling back to best available: {best_match}")
        return best_match
        
    logger.info(f"No local match found for '{semantic_query}'. Attempting FreeSound API JIT fetch...")
    url = "https://freesound.org/apiv2/search/text/"
    params = {
        "query": semantic_query,
        "filter": 'license:"Creative Commons 0"',
        "fields": "name,previews",
        "token": FREESOUND_API_KEY,
        "page_size": 1
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("results"):
            result = data["results"][0]
            download_url = result["previews"]["preview-hq-mp3"]
            safe_filename = "".join(c for c in result["name"] if c.isalnum() or c in "._- ").rstrip()
            target_path = os.path.join(DYNAMIC_DIR, f"{safe_filename}.mp3")
            relative_target_path = os.path.relpath(target_path, ASSETS_DIR)
            
            os.makedirs(DYNAMIC_DIR, exist_ok=True)
            
            # Stream down the file
            audio_data = requests.get(download_url, timeout=20)
            audio_data.raise_for_status()
            with open(target_path, "wb") as audio_file:
                audio_file.write(audio_data.content)
                
            # Update manifest dynamically
            manifest[relative_target_path] = {"tags": f"{semantic_query} downloaded dynamic {safe_filename.lower()}"}
            with open(MANIFEST_PATH, "w") as f:
                json.dump(manifest, f, indent=4)
                
            logger.info(f"Successfully JIT fetched asset: {relative_target_path}")
            return relative_target_path
    except Exception as e:
        logger.error(f"FreeSound JIT fetch failed for '{semantic_query}': {e}")
        
    logger.warning(f"Could not source asset for '{semantic_query}'. Using fallback: {best_match}")
    return best_match

def index_local_music(base_dir: str = None) -> str:
    """
    Scans the asset manifest to provide semantic suggestions to the Director.
    """
    if not os.path.exists(MANIFEST_PATH):
        return "No local music found in library. Assume default 'bgm.mp3' will be used."
        
    with open(MANIFEST_PATH, "r") as f:
        manifest = json.load(f)
        
    menu = "=== AVAILABLE BACKGROUND MUSIC & SFX (SEMANTIC AUDIO) ===\n"
    menu += "You no longer need to select an exact filename.\n"
    menu += "Instead, provide a 'semantic query' describing the vibe you want.\n"
    menu += "Examples of current local asset tags:\n"
    
    # Just list some tags to give the AI an idea
    count = 0
    for path, meta in manifest.items():
        if count > 10: break
        menu += f"- {meta.get('tags', '')}\n"
        count += 1
        
    return menu
