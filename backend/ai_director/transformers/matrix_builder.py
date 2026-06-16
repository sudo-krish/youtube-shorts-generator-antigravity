import logging
import json
from typing import List, Dict
from .video_siglip import SigLIPVideoTransformer
from .spatial_videomae import SpatialFlowTransformer

class SemanticMatrixBuilder:
    def __init__(self, video_path: str, game_id: int = None):
        self.video_path = video_path
        self.game_id = game_id
        self.logger = logging.getLogger(self.__class__.__name__)
        self.video_transformer = SigLIPVideoTransformer()
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
        from .audio_clap import ClapAudioTransformer
        duration = self.get_duration()
        self.logger.info(f"Building Audio Timeline for {duration:.2f} seconds...")
        matrix = []
        transformer = ClapAudioTransformer(game_id=self.game_id)
        transformer.load_model()
        try:
            for t in range(0, int(duration), step):
                audio_tags = transformer.process(self.video_path, t, t + step)
                matrix.append({"t_float": float(t), "audio_tags": audio_tags})
        finally:
            transformer.unload_model()
        return matrix

    def build_visual_matrix(self, step: int = 3) -> List[Dict]:
        duration = self.get_duration()
        self.logger.info(f"Building Visual Timeline for {duration:.2f} seconds...")
        matrix = []
        self.video_transformer.load_model()
        try:
            for t in range(0, int(duration), step):
                visual_tags = self.video_transformer.process(self.video_path, t, t + step)
                matrix.append({"t_float": float(t), "visual_tags": visual_tags})
        finally:
            self.video_transformer.unload_model()
        return matrix

    def build_spatial_matrix(self, step: int = 3) -> List[Dict]:
        duration = self.get_duration()
        self.logger.info(f"Building Spatial Timeline for {duration:.2f} seconds...")
        matrix = []
        self.spatial_transformer.load_model()
        try:
            for t in range(0, int(duration), step):
                spatial_tags = self.spatial_transformer.process(self.video_path, t, t + step)
                matrix.append({"t_float": float(t), "spatial_tags": spatial_tags})
        finally:
            self.spatial_transformer.unload_model()
        return matrix

    def merge_matrices(self, audio_matrix: List[Dict], visual_matrix: List[Dict], spatial_matrix: List[Dict]) -> Dict:
        return {
            "audio_timeline": audio_matrix,
            "visual_timeline": visual_matrix,
            "spatial_timeline": spatial_matrix
        }
