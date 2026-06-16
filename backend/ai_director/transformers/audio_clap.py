import torch
import gc
import librosa
import numpy as np
from transformers import pipeline
from .base import BaseTransformer

class ClapAudioTransformer(BaseTransformer):
    def __init__(self, game_id: int = None):
        super().__init__()
        self.model = None
        self.waveform = None
        self.sampling_rate = None
        self.current_video_path = None
        
        self.logger.info("CLAP: Using consolidated Micro-Chunk RMS audio strategy profile.")
        self.candidate_labels = [
            "loud gunshot or heavy gunfire",
            "weapon reloading mechanical click",
            "fast footsteps running",
            "planting bomb or defusing beeping",
            "heavy explosion blast",
            "sword slash or knife swing",
            "victory cheer or fanfare",
            "dying groan or scream"
        ]

    def load_model(self):
        if self.model is None:
            device = 0 if torch.cuda.is_available() else -1
            target_device = "VRAM" if device == 0 else "CPU"
            self.logger.info(f"CLAP: Loading zero-shot-audio-classification model into {target_device}...")
            self.model = pipeline(
                task="zero-shot-audio-classification", 
                model="laion/clap-htsat-unfused",
                device=device
            )

    def unload_model(self):
        if self.model is not None:
            self.logger.info("CLAP: Unloading model and clearing VRAM cache...")
            del self.model
            self.model = None
            self.waveform = None
            self.current_video_path = None
            if torch.cuda.is_available():
                gc.collect()
                torch.cuda.empty_cache()

    def process(self, video_path: str, start_time: float, end_time: float) -> list:
        if self.current_video_path != video_path or self.waveform is None:
            self.logger.info(f"CLAP: Loading waveform for {video_path}...")
            try:
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    self.waveform, self.sampling_rate = librosa.load(video_path, sr=48000)
                self.current_video_path = video_path
            except Exception as e:
                self.logger.error(f"CLAP: Failed to load audio waveform: {e}")
                return []

        start_sample = int(start_time * self.sampling_rate)
        end_sample = int(end_time * self.sampling_rate)
        chunk_waveform = self.waveform[start_sample:end_sample]

        if len(chunk_waveform) == 0:
            return []

        # 1. Calculate the Root Mean Square (Volume) of the chunk
        rms_volume = np.mean(librosa.feature.rms(y=chunk_waveform))
        
        # 2. If it's too quiet (e.g., just ambient map noise), skip CLAP entirely
        if rms_volume < 0.01:
            return []

        results = self.model(chunk_waveform, candidate_labels=self.candidate_labels)
        
        # Filter out low-confidence guesses (raised threshold to 0.25 to kill noise)
        valid_tags = [f"{res['label']}:{round(res['score'], 2)}" for res in results if res['score'] > 0.25]
        return valid_tags
