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

    def process(self, video_path: str, start_time: float, end_time: float, previous_context: list = None, game_name: str = "") -> list:
        if not self.model:
            self.logger.warning("Llava: Model not loaded. Returning empty.")
            return ["No visual data (Model not loaded)."]
        
        fd, temp_path = tempfile.mkstemp(suffix=".mp4")
        os.close(fd)
        
        try:
            # 1. Generate annotated video chunk using YOLO
            import cv2
            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps <= 0: fps = 30
            
            start_frame = int(start_time * fps)
            end_frame = int(end_time * fps)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
            
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(temp_path, fourcc, fps, (width, height))
            
            from app.transformers.yolo_tracker import YoloPlayerTracker
            yolo = YoloPlayerTracker()
            yolo.load_model()
            
            COLORS = {"enemy": (0, 0, 255), "weapon": (255, 0, 0), "minimap": (0, 255, 0)}
            
            for _ in range(start_frame, end_frame):
                ret, frame = cap.read()
                if not ret: break
                
                f_h, f_w = frame.shape[:2]
                candidates = yolo._process_frame_for_camera(frame, f_h, f_w)
                
                for det in candidates:
                    label = "ENEMY"
                    cx, cy, w, h = det["cx"], det["cy"], det["w"], det["h"]
                    x1, y1 = int(cx - w/2), int(cy - h/2)
                    x2, y2 = int(cx + w/2), int(cy + h/2)
                    
                    color = COLORS.get(label.lower(), (0, 0, 255))
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness=3)
                    
                    text = f"[{label}]"
                    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
                    cv2.rectangle(frame, (x1, y1 - 25), (x1 + tw, y1), (0, 0, 0), -1)
                    cv2.putText(frame, text, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                
                out.write(frame)
                
            cap.release()
            out.release()
            yolo.unload_model() # Free YOLO VRAM
            
            # 2. The Prompt Injection (LLaVA Play-by-Play Pass)
            if previous_context is None:
                previous_context = []
                
            history_prompt = ""
            if len(previous_context) > 0:
                # To prevent overloading, we keep the last 30 events if the video is extremely long
                recent_history = previous_context[-30:]
                history_prompt = "Recent timeline of events leading up to this clip:\n" + "\n".join(recent_history) + "\n\n"
            
            game_prompt = f"Game context: {game_name.capitalize()}.\n" if game_name else ""
            
            # NEW: Highly structured prompt demanding a chronological timeline
            duration = end_time - start_time
            prompt_text = (
                f"{history_prompt}{game_prompt}You are an expert esports play-by-play commentator analyzing a short video clip. "
                f"This clip starts at EXACTLY {start_time:.1f}s and ends at {end_time:.1f}s of the match. "
                "Break down the action into a chronological timeline for ONLY this timeframe. "
                f"You MUST use absolute timestamps between {start_time:.1f}s and {end_time:.1f}s. "
                "Keep each description under 10 words. "
                "Look specifically for the [ENEMY] bounding boxes to identify firefights. "
                "Format strictly like this:\n"
                f"{start_time + (duration*0.2):.1f}s: Player walking holding rifle.\n"
                f"{start_time + (duration*0.5):.1f}s: Player spots [ENEMY] and aims.\n"
                f"{start_time + (duration*0.8):.1f}s: Player shoots at [ENEMY].\n"
                "Provide the timeline now:"
            )
            
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "video", "video": temp_path},
                        {"type": "text", "text": prompt_text},
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
            
            # NEW: Expanded generation limits to allow the full story to be written
            generated_ids = self.model.generate(
                **inputs, 
                max_new_tokens=150,       # Bumped from 30 to 150 to fit the timeline
                repetition_penalty=1.15,  # Prevents repeating the exact same sentence
                no_repeat_ngram_size=3,   # Prevents hallucination loops
                temperature=0.3,          # Low temp keeps it factual instead of creative
                do_sample=True
            )
            
            input_length = len(inputs["input_ids"][0])
            output_text = self.processor.batch_decode(
                generated_ids[:, input_length:], skip_special_tokens=True, clean_up_tokenization_spaces=False
            )
            
            timeline_description = output_text[0].strip()
            self.logger.info(f"Llava Play-by-Play Timeline:\n{timeline_description}")
            return [timeline_description]
            
        except Exception as e:
            self.logger.error(f"Llava failed processing annotated chunk: {e}")
            return ["Error during visual extraction."]
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
