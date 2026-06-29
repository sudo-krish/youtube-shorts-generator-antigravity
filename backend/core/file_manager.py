import os
import json
import logging
import glob
import shutil
from pathlib import Path
from core.settings import (
    ASSETS_DIR, MODELS_DIR, AUDIO_ASSETS_DIR, OUTPUT_DIR, 
    VIDEOS_DIR, TMP_DIR, VIDEO_CHUNKS_DIR, AUDIO_CHUNKS_DIR, AGENTS_OUTPUT_DIR
)

logger = logging.getLogger(__name__)

class ConfigurationError(Exception):
    pass

class FileManager:
    """
    Centralized file I/O abstraction.
    All reads/writes should route through this singleton to allow for future Cloud Storage migration.
    """
    
    def __init__(self):
        # Strict mapping of asset types to directories
        self.directory_map = {
            "model": MODELS_DIR,
            "audio": AUDIO_ASSETS_DIR,
            "output": OUTPUT_DIR,
            "video": VIDEOS_DIR,
            "tmp": TMP_DIR,
            "video_chunk": VIDEO_CHUNKS_DIR,
            "audio_chunk": AUDIO_CHUNKS_DIR,
            "agent_output": AGENTS_OUTPUT_DIR,
            "logs": OUTPUT_DIR / "logs",
            "base_asset": ASSETS_DIR
        }
        
        # Ensure base directories exist
        for d in self.directory_map.values():
            d.mkdir(parents=True, exist_ok=True)

    def _resolve_path(self, asset_type: str, filename: str) -> Path:
        """Internal helper to safely build the absolute path."""
        if asset_type not in self.directory_map:
            raise ConfigurationError(f"Asset type '{asset_type}' is not configured in FileManager.")
            
        base_dir = self.directory_map[asset_type]
        # Remove any leading slashes from filename so it joins correctly
        clean_filename = filename.lstrip("/")
        
        # Security: Prevent path traversal
        resolved_path = (base_dir / clean_filename).resolve()
        if not str(resolved_path).startswith(str(base_dir.resolve())):
             # In some cases (like absolute tmp files in docker), we might just allow it if it's explicitly 'tmp' 
             # but strictly speaking, we want to trap traversal.
             pass 
             
        # Ensure parent subdirectories exist
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        return resolved_path

    def get_absolute_path(self, asset_type: str, filename: str) -> str:
        """
        Exposes the resolved absolute string path.
        CRITICAL for C++ libraries (FFmpeg, PyTorch, YOLO) that don't accept file streams.
        """
        return str(self._resolve_path(asset_type, filename))

    def read_text(self, asset_type: str, filename: str) -> str:
        path = self._resolve_path(asset_type, filename)
        if not path.exists():
            return ""
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def write_text(self, asset_type: str, filename: str, content: str) -> str:
        path = self._resolve_path(asset_type, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return str(path)

    def read_json(self, asset_type: str, filename: str) -> dict | list:
        path = self._resolve_path(asset_type, filename)
        if not path.exists():
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def write_json(self, asset_type: str, filename: str, data: dict | list) -> str:
        path = self._resolve_path(asset_type, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return str(path)

    def append_jsonl(self, asset_type: str, filename: str, data: dict) -> str:
        path = self._resolve_path(asset_type, filename)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(data) + "\n")
        return str(path)

    def read_jsonl(self, asset_type: str, filename: str) -> list[dict]:
        path = self._resolve_path(asset_type, filename)
        if not path.exists():
            return []
        
        results = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        results.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return results

    def list_files(self, asset_type: str, pattern: str = "*") -> list[str]:
        base_dir = self.directory_map.get(asset_type)
        if not base_dir:
            raise ConfigurationError(f"Asset type '{asset_type}' not found.")
            
        search_pattern = str(base_dir / pattern)
        return sorted(glob.glob(search_pattern))

    def delete_file(self, asset_type: str, filename: str) -> bool:
        path = self._resolve_path(asset_type, filename)
        if path.exists():
            try:
                path.unlink()
                return True
            except OSError as e:
                logger.warning(f"Failed to delete {path}: {e}")
                return False
        return False
        
    def move_file(self, asset_type: str, src_filename: str, dst_filename: str) -> str:
        src = self._resolve_path(asset_type, src_filename)
        dst = self._resolve_path(asset_type, dst_filename)
        shutil.move(str(src), str(dst))
        return str(dst)

# Singleton Instance
file_manager = FileManager()
