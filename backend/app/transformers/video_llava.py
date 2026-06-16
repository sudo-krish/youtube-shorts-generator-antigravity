import torch
import gc
import logging
import subprocess
import tempfile
import os
from transformers import AutoProcessor, LlavaOnevisionForConditionalGeneration
from .base import BaseTransformer

class LlavaVideoTransformer(BaseTransformer):
    def __init__(self):
        super().__init__()
        self.model_id = "llava-hf/llava-onevision-qwen2-0.5b-ov-hf"
        self.model = None
        self.processor = None
        self.logger = logging.getLogger(self.__class__.__name__)

    def load_model(self):
        self.logger.info("Llava: Loading Qwen-0.5b Video Vision Model into VRAM...")
        from core.settings import MODELS_DIR
        
        # device_map="auto" automatically handles CUDA placement.
        self.processor = AutoProcessor.from_pretrained(
            self.model_id,
            cache_dir=str(MODELS_DIR)
        )
        self.model = LlavaOnevisionForConditionalGeneration.from_pretrained(
            self.model_id, 
            device_map="auto", 
            torch_dtype=torch.float16,
            cache_dir=str(MODELS_DIR)
        )
        self.logger.info("Llava: Loaded successfully.")

    def unload_model(self):
        self.logger.info("Llava: Unloading model to free VRAM...")
        if self.model is not None:
            del self.model
        if self.processor is not None:
            del self.processor
            
        self.model = None
        self.processor = None
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            gc.collect()

    def process(self, video_path: str, start_time: float, end_time: float) -> list:
        if not self.model:
            self.logger.warning("Llava: Model not loaded. Returning empty.")
            return ["No visual data (Model not loaded)."]
        
        fd, temp_path = tempfile.mkstemp(suffix=".mp4")
        os.close(fd)
        
        try:
            # We use FFmpeg to extract exactly the temporal chunk needed.
            # Using ultrafast to minimize I/O block time. We only need visual data, so -an.
            subprocess.run([
                "ffmpeg", "-y", "-i", video_path, 
                "-ss", str(start_time), "-to", str(end_time),
                "-c:v", "libx264", "-preset", "ultrafast", "-an",
                temp_path
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "video", "video": temp_path},
                        {"type": "text", "text": "Describe exactly what is happening in this video clip. Detail the actions, UI elements, and overall environment. Keep it concise."},
                    ],
                }
            ]
            
            inputs = self.processor.apply_chat_template(
                messages,
                tokenize=True,
                add_generation_prompt=True,
                return_dict=True,
                return_tensors="pt",
                num_frames=10,
                do_sample_frames=True
            ).to(self.model.device)
            
            # Offload generation constraint to keep it quick
            generated_ids = self.model.generate(**inputs, max_new_tokens=64)
            input_length = len(inputs["input_ids"][0])
            output_text = self.processor.batch_decode(
                generated_ids[:, input_length:], skip_special_tokens=True, clean_up_tokenization_spaces=False
            )
            
            description = output_text[0].strip()
            self.logger.info(f"Llava extracted: {description}")
            return [description]
            
        except Exception as e:
            self.logger.error(f"Llava failed processing chunk: {e}")
            return ["Error during visual extraction."]
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
