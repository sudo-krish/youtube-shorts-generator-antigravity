import logging
import torch
import gc
from typing import List
from google.genai import types
from PIL import Image
import base64
import io
import os
from ..llm_client import BaseLLMClient
from modules.ai.service import ai_service

class QwenVLClient(BaseLLMClient):
    """
    Native HuggingFace implementation for Qwen2-VL-2B-Instruct.
    Runs strictly in float16 to remain under the 6GB VRAM limit.
    """
    
    _model = None
    _processor = None
    
    def __init__(self):
        super().__init__()
        # We lazy load the model to avoid booting it into VRAM immediately upon app start
        
    def _load_model(self):
        if QwenVLClient._model is None:
            self.logger.info("Loading Qwen2-VL-2B-Instruct into VRAM (float16)...")
            from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
            from core.file_manager import file_manager
            
            # Use float16 which requires ~4.5GB VRAM
            QwenVLClient._model = Qwen2VLForConditionalGeneration.from_pretrained(
                "Qwen/Qwen2-VL-2B-Instruct", 
                torch_dtype=torch.float16, 
                device_map="auto",
                cache_dir=file_manager.get_absolute_path("model", "")
            )
            QwenVLClient._processor = AutoProcessor.from_pretrained(
                "Qwen/Qwen2-VL-2B-Instruct",
                cache_dir=file_manager.get_absolute_path("model", "")
            )
            self.logger.info("Qwen2-VL successfully loaded.")
            
    def _parse_contents(self, contents: List) -> List[dict]:
        """Converts standard Gemini-style contents array into Qwen message format."""
        # For this specialized pipeline, we expect [image_path, text_prompt] or similar.
        qwen_content = []
        for item in contents:
            if isinstance(item, str):
                # Check if it's an image path (simple heuristic)
                if item.endswith(".jpg") or item.endswith(".png") or item.endswith(".jpeg"):
                    if os.path.exists(item):
                        image = Image.open(item).convert("RGB")
                        qwen_content.append({"type": "image", "image": image})
                    else:
                        qwen_content.append({"type": "text", "text": f"[Missing Image: {item}]"})
                else:
                    qwen_content.append({"type": "text", "text": item})
            else:
                qwen_content.append({"type": "text", "text": str(item)})
                
        return [{"role": "user", "content": qwen_content}]
        
    def generate_content(
        self, model: str, contents: list, config: types.GenerateContentConfig = None
    ) -> str:
        self._load_model()
        
        try:
            messages = self._parse_contents(contents)
            
            # Preparation using processor
            text = QwenVLClient._processor.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            
            image_inputs = []
            for msg in messages:
                for c in msg["content"]:
                    if c["type"] == "image":
                        image_inputs.append(c["image"])
                        
            if not image_inputs:
                image_inputs = None
                
            inputs = QwenVLClient._processor(
                text=[text],
                images=image_inputs,
                padding=True,
                return_tensors="pt",
            )
            inputs = inputs.to(QwenVLClient._model.device)
            
            # Generate
            # Enforce max tokens depending on config or default to something safe
            max_tokens = 128
            if config and hasattr(config, "max_output_tokens") and config.max_output_tokens:
                max_tokens = config.max_output_tokens
                
            generated_ids = QwenVLClient._model.generate(**inputs, max_new_tokens=max_tokens)
            generated_ids_trimmed = [
                out_ids[len(in_ids) :] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
            ]
            output_text = QwenVLClient._processor.batch_decode(
                generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
            )[0]
            
            # Log zero usage since it's local
            try:
                model_id = ai_service.get_or_create_model("qwen_vl", "Qwen2-VL-2B-Instruct")
                ai_service.log_usage(model_id, len(inputs.input_ids[0]), len(generated_ids_trimmed[0]), 0.0)
            except Exception as e:
                self.logger.warning(f"Failed to log Qwen usage: {e}")
                
            return output_text
            
        finally:
            # Free some memory (optional, but good for tight 6GB limits)
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                gc.collect()
