import os
import logging

logger = logging.getLogger(__name__)

def index_local_music(base_dir: str = None) -> str:
    """
    Scans the local audio library to provide a list of available
    background music (BGM) tracks for the Director agent.
    """
    if base_dir is None:
        base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "downloads", "audio_library")
        
    if not os.path.exists(base_dir):
        os.makedirs(base_dir, exist_ok=True)
        # Create a default if empty to show the AI how to use it
        open(os.path.join(base_dir, "hype_trap_beat.mp3"), 'a').close()
        open(os.path.join(base_dir, "sad_violin.mp3"), 'a').close()
        
    available_files = []
    for root, _, files in os.walk(base_dir):
        for file in files:
            if file.endswith(('.mp3', '.wav', '.m4a')):
                available_files.append(file)
                
    if not available_files:
        return "No local music found in library. Assume default 'bgm.mp3' will be used."
        
    menu = "=== AVAILABLE BACKGROUND MUSIC (SEMANTIC AUDIO) ===\n"
    menu += "You MUST select exactly one of these filenames for the `background_audio_track` field:\n"
    for f in available_files[:50]:
        menu += f"- {f}\n"
        
    return menu
