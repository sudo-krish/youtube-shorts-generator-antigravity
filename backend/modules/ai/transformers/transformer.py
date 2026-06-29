import logging
import torch
import gc
from core.file_manager import file_manager

class BaseTransformer:
    name: str = "generic"

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
        self.processor = None
        self.logger = logging.getLogger(self.__class__.__name__)

    def load_model(self):
        """Override this in child classes to implement specific model loading."""
        pass

    def unload_model(self):
        """Override this in child classes to implement specific memory cleanup."""
        pass

    def process(self, payload: dict) -> dict:
        raise NotImplementedError("process method must be overridden in child classes.")

    async def execute(self, payload: dict) -> dict:
        from core.locks import acquire_vram_lock, release_vram_lock
        lock_name = f"{self.name.capitalize()}Transformer"
        
        self.logger.info(f"Running {lock_name} with payload: {payload}")
        await acquire_vram_lock(lock_name)
        self.load_model()
        try:
            result = self.process(payload)
        finally:
            self.unload_model()
            release_vram_lock(lock_name)
        return result


def get_all_transformers():
    # Lazy imports to prevent circular dependencies since the utils import BaseTransformer from here
    from .models.yolo_tracker import YoloPlayerTracker
    
    return {
        "yolo": YoloPlayerTracker
    }
