import logging
from abc import ABC, abstractmethod
from google.genai import types

class BaseLLMClient(ABC):
    """Abstract base class for LLM providers (Gemini, DeepSeek, Ollama, etc.)"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def generate_content(
        self, model: str, contents: list, config: types.GenerateContentConfig = None
    ) -> str:
        """
        Generates content from the LLM. 
        Implementations should handle retries, cost tracking, and rate limiting internally.
        """
        pass

def get_llm_client(model_name: str) -> BaseLLMClient:
    """
    Returns the appropriate LLM Client Strategy based on the model name prefix.
    Supports 'deepseek', 'ollama', and defaults to 'gemini' for everything else.
    """
    model_lower = model_name.lower()
    
    if model_lower.startswith("deepseek"):
        from .models.deepseek import DeepSeekClient
        return DeepSeekClient()
        
    elif model_lower.startswith("ollama"):
        from .models.ollama import OllamaClient
        return OllamaClient()
        
    elif model_lower.startswith("qwen"):
        from .models.qwen_vl import QwenVLClient
        return QwenVLClient()
        
    else:
        # Default to Google GenAI for standard model strings like "gemini-1.5-pro"
        from .models.gemini import GeminiClient
        return GeminiClient()
