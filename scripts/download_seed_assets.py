import os
import json
import subprocess
import urllib.request
import zipfile
import shutil
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# To avoid massive downloads, we will synthesize high-quality seed assets using FFmpeg 
# to represent the local cache. In a real environment, the user can manually drop Kenney 
# packs into this folder and rerun the script.
ASSETS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", "assets"))
MANIFEST_PATH = os.path.join(ASSETS_DIR, "asset_manifest.json")
DYNAMIC_DIR = os.path.join(ASSETS_DIR, "sfx", "dynamic")

SFX_RECIPES = {
    "Impacts/heavy_explosion.wav": ["ffmpeg", "-y", "-f", "lavfi", "-i", "aevalsrc='sin(400*exp(-t*4)*t)*exp(-t*2)':d=1", "-af", "volume=5"],
    "Impacts/deep_sub_drop.wav": ["ffmpeg", "-y", "-f", "lavfi", "-i", "aevalsrc='sin(100*exp(-t*2)*t)':d=3", "-af", "volume=3"],
    "Transitions/digital_glitch.wav": ["ffmpeg", "-y", "-f", "lavfi", "-i", "anoisesrc=c=brown:d=0.5", "-af", "aeval='val*sin(t*50)*exp(-t*5)',volume=2"],
    "Transitions/cinematic_whoosh.wav": ["ffmpeg", "-y", "-f", "lavfi", "-i", "anoisesrc=c=pink:d=1.5", "-af", "aeval='val*sin(t*3)*exp(-t*3)',volume=5"],
    "UI/soft_click.wav": ["ffmpeg", "-y", "-f", "lavfi", "-i", "aevalsrc='sin(1000*t)*exp(-t*50)':d=0.1", "-af", "volume=2"],
    "UI/success_chime.wav": ["ffmpeg", "-y", "-f", "lavfi", "-i", "aevalsrc='sin(800*t)*exp(-t*4) + sin(1200*t)*exp(-t*4)':d=1", "-af", "volume=1"],
    "Music/cyberpunk_bass.wav": ["ffmpeg", "-y", "-f", "lavfi", "-i", "aevalsrc='sin(50*t)*exp(-t*0.5)':d=5", "-af", "volume=2"],
    "Music/chill_lofi_pad.wav": ["ffmpeg", "-y", "-f", "lavfi", "-i", "aevalsrc='sin(300*t)*exp(-t*0.2) * sin(t)':d=5", "-af", "volume=1"],
}

def generate_seed_assets():
    os.makedirs(ASSETS_DIR, exist_ok=True)
    os.makedirs(DYNAMIC_DIR, exist_ok=True)
    
    manifest = {}
    
    for relative_path, cmd_base in SFX_RECIPES.items():
        filepath = os.path.join(ASSETS_DIR, relative_path)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        if not os.path.exists(filepath):
            logger.info(f"Synthesizing seed asset: {relative_path}")
            cmd = cmd_base + [filepath]
            try:
                subprocess.run(cmd, check=True, capture_output=True)
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to synthesize {relative_path}: {e.stderr.decode()}")
                continue
                
        # Generate tags based on folder name and file name
        folder_tag = os.path.basename(os.path.dirname(relative_path)).lower()
        file_tag = os.path.basename(relative_path).replace(".wav", "").replace("_", " ").lower()
        
        manifest[relative_path] = {
            "tags": f"{folder_tag} {file_tag} synthesized seed"
        }
        
    # Write the manifest
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=4)
        
    logger.info(f"Asset Bootstrapping Complete. Manifest written to {MANIFEST_PATH}")
    logger.info(f"Total localized assets indexed: {len(manifest)}")

if __name__ == "__main__":
    generate_seed_assets()
