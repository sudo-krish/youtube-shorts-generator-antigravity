import os
import logging

logger = logging.getLogger(__name__)

def index_local_sfx(base_dir: str = None) -> str:
    """
    Scans the local SFX and Music folders to provide a list of available
    audio files for the Director agent to use.
    """
    if base_dir is None:
        base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets")
        
    sfx_dir = os.path.join(base_dir, "sfx")
    
    if not os.path.exists(sfx_dir):
        return "No local SFX library found. You may suggest generic SFX names like 'vine_boom.mp3'."
        
    available_files = []
    for root, _, files in os.walk(sfx_dir):
        for file in files:
            if file.endswith(('.mp3', '.wav', '.m4a')):
                available_files.append(file)
                
    if not available_files:
        return "No local SFX files found in library. Use generic names."
        
    menu = "=== AVAILABLE LOCAL SFX LIBRARY ===\n"
    for f in available_files[:50]: # Limit to avoid token bloat
        menu += f"- {f}\n"
        
    return menu
