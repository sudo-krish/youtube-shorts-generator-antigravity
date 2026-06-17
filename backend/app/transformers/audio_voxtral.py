import torch
import librosa
import gc
from transformers import VoxtralForConditionalGeneration, AutoProcessor
from .base import BaseTransformer

class AudioVoxtralTransformer(BaseTransformer):
    def __init__(self, game_id: str = None):
        super().__init__()
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.repo_id = "mistralai/Voxtral-Mini-3B-2507" # The 3B model fits in 6GB VRAM
        self.processor = None
        self.model = None
        self.game_id = game_id

    def load_model(self):
        from core.settings import MODELS_DIR
        self.logger.info("Loading Voxtral-Mini-3B Processor...")
        self.processor = AutoProcessor.from_pretrained(
            self.repo_id,
            cache_dir=str(MODELS_DIR)
        )
        
        self.logger.info(f"Loading Voxtral Model into {self.device.upper()} VRAM...")
        # device_map="auto" and bfloat16 keep memory usage under 4GB
        self.model = VoxtralForConditionalGeneration.from_pretrained(
            self.repo_id, 
            dtype=torch.bfloat16, 
            device_map=self.device,
            cache_dir=str(MODELS_DIR)
        )

    def unload_model(self):
        if self.model is not None:
            self.logger.info("Unloading Audio Model and clearing VRAM...")
            del self.model
            del self.processor
            self.model = None
            self.processor = None
            if self.device == "cuda":
                gc.collect()
                torch.cuda.empty_cache()

    def process(self, video_path: str, start_time: float, end_time: float) -> str:
        import tempfile
        import os
        import soundfile as sf
        
        try:
            # Load the specific chunk using librosa
            waveform, sr = librosa.load(video_path, sr=16000, offset=start_time, duration=(end_time - start_time))
            
            if len(waveform) == 0:
                return "Silence."
                
            # Voxtral's chat template requires audio to be passed via a file path or URL
            fd, temp_path = tempfile.mkstemp(suffix=".wav")
            os.close(fd)
            
            try:
                sf.write(temp_path, waveform, sr)
                
                # The Master Prompt: Tell the model exactly what to listen for
                system_prompt = (
                    "Listen to this brief gaming audio clip. "
                    "Identify any gunshots, explosions, footsteps, or UI sounds. "
                    "If the player speaks, transcribe what they say and describe their emotional state. "
                    "Keep the answer to one concise sentence."
                )
    
                # Build the conversation payload natively
                conversation = [
                    {"role": "user", "content": [
                        {"type": "text", "text": f"{system_prompt}\n\nWhat is happening in this audio?"},
                        {"type": "audio", "path": temp_path}
                    ]}
                ]
    
                inputs = self.processor.apply_chat_template(
                    conversation,
                    tokenize=True,
                    return_dict=True
                )
                
                # Move inputs to VRAM in bfloat16
                inputs = {k: v.to(self.device, dtype=torch.bfloat16) if torch.is_floating_point(v) else v.to(self.device) for k, v in inputs.items()}
    
                # Generate the description
                with torch.no_grad():
                    outputs = self.model.generate(**inputs, max_new_tokens=100)
                
                # Decode the output
                decoded_output = self.processor.batch_decode(
                    outputs[:, inputs["input_ids"].shape[1]:], 
                    skip_special_tokens=True
                )[0]
    
                return decoded_output.strip()
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
        except Exception as e:
            self.logger.error(f"Voxtral failed to process chunk {start_time}-{end_time}: {e}")
            return "Audio processing failed."
