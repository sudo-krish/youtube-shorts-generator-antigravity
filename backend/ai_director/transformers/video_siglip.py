import numpy as np
import cv2
from huggingface_hub import hf_hub_download
from tokenizers import Tokenizer
from .base import BaseTransformer

class SigLIPVideoTransformer(BaseTransformer):
    def __init__(self):
        super().__init__()
        self.repo_id = "Xenova/siglip-base-patch16-224"
        self.session = None
        self.tokenizer = None
        
        self.vocab = [
            "playing a first person shooter game",
            "aiming down the sights of a gun",
            "firing a weapon with muzzle flash",
            "an enemy player character visible",
            "reloading a weapon",
            "navigating a dark corridor or room",
            "killfeed text updating in the corner",
            "dead and spectating another player",
            "in a menu or buy phase"
        ]
        
        self.input_ids = None

    def load_model(self):
        import onnxruntime as ort
        self.logger.info("SigLIP: Loading tokenizer and ONNX models via HuggingFace Hub...")
        
        tok_path = hf_hub_download(repo_id=self.repo_id, filename="tokenizer.json")
        self.tokenizer = Tokenizer.from_file(tok_path)
        
        # Pre-tokenize the vocabulary
        input_ids = []
        for tag in self.vocab:
            encoded = self.tokenizer.encode(tag)
            ids = encoded.ids
            if len(ids) < 64:
                ids = ids + [0]*(64-len(ids))
            else:
                ids = ids[:64]
            input_ids.append(ids)
            
        self.input_ids = np.array(input_ids, dtype=np.int64)
        
        model_path = hf_hub_download(repo_id=self.repo_id, filename="onnx/model_quantized.onnx")
        sess_options = ort.SessionOptions()
        sess_options.intra_op_num_threads = 2
        
        # CPU execution for RAM bound inference
        self.session = ort.InferenceSession(model_path, sess_options, providers=["CPUExecutionProvider"])
        self.logger.info("SigLIP: Model loaded successfully.")
        
    def unload_model(self):
        self.logger.info("SigLIP: Unloading model and triggering garbage collection.")
        self.session = None
        
    def _extract_frame(self, video_path: str, time_sec: float) -> np.ndarray:
        cap = cv2.VideoCapture(video_path)
        cap.set(cv2.CAP_PROP_POS_MSEC, time_sec * 1000.0)
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            return np.zeros((224, 224, 3), dtype=np.uint8)
            
        return frame
        
    def _normalize_frame(self, frame: np.ndarray) -> np.ndarray:
        frame = cv2.resize(frame, (224, 224), interpolation=cv2.INTER_CUBIC)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = frame.astype(np.float32) / 255.0
        
        mean = np.array([0.5, 0.5, 0.5], dtype=np.float32)
        std = np.array([0.5, 0.5, 0.5], dtype=np.float32)
        frame = (frame - mean) / std
        
        frame = np.transpose(frame, (2, 0, 1))
        return frame[np.newaxis, ...] # [1, 3, 224, 224]

    def process(self, video_path: str, start_time: float, end_time: float) -> list:
        if not self.session:
            self.logger.warning("SigLIP: Session not loaded. Returning empty tags.")
            return []
            
        # Extract a frame in the middle of the time window
        mid_time = start_time + ((end_time - start_time) / 2.0)
        frame = self._extract_frame(video_path, mid_time)
        pixel_values = self._normalize_frame(frame)
        
        # Batching: we duplicate the image N times to match the N text prompts
        num_tags = len(self.vocab)
        pixel_values_batch = np.repeat(pixel_values, num_tags, axis=0)
        
        outputs = self.session.run(None, {
            "pixel_values": pixel_values_batch,
            "input_ids": self.input_ids
        })
        
        logits = outputs[0][0] # Taking the first batch output is equivalent (all images are the same)
        
        # Sigmoid for probabilities
        probs = 1 / (1 + np.exp(-logits))
        
        # Get top tags
        top_indices = np.argsort(probs)[-2:][::-1]
        tags = []
        for idx in top_indices:
            if probs[idx] > 0.15: 
                clean_tag = self.vocab[idx].replace("a photo of ", "").replace(" ", "_").lower()
                tags.append(f"{clean_tag}:{probs[idx]:.2f}")
                
        return tags
