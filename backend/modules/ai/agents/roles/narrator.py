import logging
from core.file_manager import file_manager
from pathlib import Path
from ..agents import BaseDynamicAgent
from ..memory.manager import ContextMemoryManager
from ..llm.llm_client import get_llm_client
from google.genai import types

class NarrativeInferenceNode(BaseDynamicAgent):
    name = "narrator"
    

    def __init__(self):
        super().__init__()
        self.memory_manager = ContextMemoryManager()
        
    def execute(self, payload: dict) -> dict:
        self.logger.info("NarrativeInferenceNode starting...")
        
        job_id = payload.get("job_id")
        frame_dir = payload.get("frame_dir", f"/tmp/jobs/{job_id}/frames")
        
        if not job_id:
            self.logger.error("Narrator failed: Missing job_id in payload")
            return {"status": "error"}
            
        # Get all frames and sort them by timestamp
        if not Path(frame_dir).exists():
            self.logger.error(f"Narrator failed: Frame directory not found {frame_dir}")
            return {"status": "error"}
            
        frame_files = sorted([str(p) for p in Path(frame_dir).glob("frame_*.jpg")])
        if not frame_files:
            return {"status": "completed", "message": "No frames to process"}
            
        client = get_llm_client("qwen")
        gen_config = types.GenerateContentConfig(temperature=0.1)
        
        processed_count = 0
        
        # We simulate the Consumer Loop here. In a true async queue, this would be a worker thread.
        # For the agent payload pattern, we process the available batch.
        for frame_path in frame_files:
            # Extract timestamp from filename e.g., frame_12.50.jpg -> 12.50
            basename = Path(frame_path).name
            try:
                timestamp = float(basename.replace("frame_", "").replace(".jpg", ""))
            except ValueError:
                continue
                
            # Fetch Context
            context = self.memory_manager.get_recent_context(job_id, timestamp)
            
            # Format Prompt
            prompt_text = (
                f"You are a video analysis AI. Describe exactly what is happening in this single frame in one concise sentence.\n\n"
                f"Recent Context (Past 5 Minutes):\n{context}\n\n"
                f"Based on the context and the image, what is happening right now at {timestamp:.2f}s? Be direct and brief."
            )
            
            contents = [frame_path, prompt_text]
            
            # Infer
            try:
                description = client.generate_content(
                    model="qwen",
                    contents=contents,
                    config=gen_config
                )
                
                # Commit
                self.memory_manager.commit(job_id, timestamp, description)
                processed_count += 1
                
                # Cleanup (Optional: remove frame after processing to free disk space)
                file_manager.delete_file("tmp", Path(frame_path).name)
                
            except Exception as e:
                self.logger.error(f"Inference failed for frame {frame_path}: {e}")
                
        return {
            "status": "success", 
            "processed_frames": processed_count,
            "message": "Narrative inference completed for available batch."
        }
