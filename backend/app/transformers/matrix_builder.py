import logging
import json
from typing import List, Dict
from .spatial_videomae import SpatialFlowTransformer

class SemanticMatrixBuilder:
    def __init__(self, video_path: str, game_id: int = None):
        self.video_path = video_path
        self.game_id = game_id
        self.logger = logging.getLogger(self.__class__.__name__)
        self.spatial_transformer = SpatialFlowTransformer()

    def get_duration(self) -> float:
        import ffmpeg
        try:
            probe = ffmpeg.probe(self.video_path)
            duration = float(probe["format"]["duration"])
            return duration
        except Exception as e:
            logger.error(f"Failed to probe duration for {self.video_path}: {e}")
            return 0.0

    def build_audio_matrix(self, step: int = 3) -> List[Dict]:
        import httpx
        duration = self.get_duration()
        self.logger.info(f"API Call: Building Audio Timeline for {duration:.2f} seconds...")
        response = httpx.post("http://127.0.0.1:8000/api/transformers/audio", json={"video_path": self.video_path, "duration": duration, "step": step, "game_id": self.game_id}, timeout=300)
        response.raise_for_status()
        return response.json().get("matrix", [])

    def build_visual_matrix(self, step: int = 3) -> List[Dict]:
        import httpx
        duration = self.get_duration()
        self.logger.info(f"API Call: Building Visual Timeline for {duration:.2f} seconds...")
        response = httpx.post("http://127.0.0.1:8000/api/transformers/vision", json={"video_path": self.video_path, "duration": duration, "step": step, "game_id": self.game_id}, timeout=300)
        response.raise_for_status()
        return response.json().get("matrix", [])

    def build_spatial_matrix(self, step: int = 3) -> List[Dict]:
        import httpx
        duration = self.get_duration()
        self.logger.info(f"API Call: Building Spatial Timeline for {duration:.2f} seconds...")
        response = httpx.post("http://127.0.0.1:8000/api/transformers/spatial", json={"video_path": self.video_path, "duration": duration, "step": step, "game_id": self.game_id}, timeout=300)
        response.raise_for_status()
        return response.json().get("matrix", [])

    def build_yolo_matrix(self, step: int = 1) -> List[Dict]:
        import httpx
        duration = self.get_duration()
        self.logger.info(f"API Call: Building YOLO Tracking Timeline for {duration:.2f} seconds...")
        response = httpx.post("http://127.0.0.1:8000/api/transformers/yolo", json={"video_path": self.video_path, "duration": duration, "step": step, "game_id": self.game_id}, timeout=300)
        response.raise_for_status()
        return response.json().get("matrix", [])

    def merge_matrices(self, audio_matrix: List[Dict], visual_matrix: List[Dict], spatial_matrix: List[Dict]) -> Dict:
        return {
            "audio_timeline": audio_matrix,
            "visual_timeline": visual_matrix,
            "spatial_timeline": spatial_matrix
        }

