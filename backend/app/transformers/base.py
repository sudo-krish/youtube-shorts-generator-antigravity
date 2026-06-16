from abc import ABC, abstractmethod
import logging

class BaseTransformer(ABC):
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def load_model(self):
        """Loads the ONNX model into memory."""
        pass
        
    @abstractmethod
    def unload_model(self):
        """Strictly unloads the model and triggers garbage collection to prevent memory leaks."""
        pass
        
    @abstractmethod
    def process(self, video_path: str, start_time: float, end_time: float) -> list:
        """Processes a segment and returns a list of semantic text tags."""
        pass
