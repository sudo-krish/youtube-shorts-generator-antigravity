import logging
from core.file_manager import file_manager
import json

class ContextMemoryManager:
    """
    Pillar 2: The State (Memory)
    Tracks the narrative timeline using flat-file JSONL logging.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.window_seconds = 300.0 # 5 minutes

    def commit(self, job_id: str, timestamp: float, description: str):
        if not description or not description.strip():
            return
            
        description = description.strip()
        filename = f"{job_id}/memory_log.jsonl"
        
        # Read all to deduplicate (inefficient but matches old logic)
        logs = file_manager.read_jsonl("agent_output", filename)
        if logs:
            last_entry = logs[-1]
            if last_entry.get("description") == description:
                last_entry["end_time"] = timestamp
                # Rewrite whole file
                # Temporary workaround since file_manager doesn't have write_jsonl
                text_lines = [json.dumps(l) for l in logs]
                file_manager.write_text("agent_output", filename, "\\n".join(text_lines) + "\\n")
                self.logger.debug(f"Extended memory for job {job_id} to {timestamp}s")
                return
                
        new_entry = {
            "job_id": job_id,
            "start_time": timestamp,
            "end_time": timestamp,
            "description": description
        }
        
        file_manager.append_jsonl("agent_output", filename, new_entry)
        self.logger.debug(f"Committed memory for job {job_id} at {timestamp}s: {description}")

    def get_recent_context(self, job_id: str, current_time: float) -> str:
        start_threshold = max(0.0, current_time - self.window_seconds)
        filename = f"{job_id}/memory_log.jsonl"
        
        try:
            logs = file_manager.read_jsonl("agent_output", filename)
            valid_logs = [l for l in logs if l.get("end_time", 0) >= start_threshold and l.get("start_time", float('inf')) <= current_time]
            
            if not valid_logs:
                return "No recent context available."
                
            context_lines = []
            for log in valid_logs:
                time_str = f"[{log['start_time']:.1f}s - {log['end_time']:.1f}s]" if log['start_time'] != log['end_time'] else f"[{log['start_time']:.1f}s]"
                context_lines.append(f"{time_str}: {log['description']}")
                
            return " ".join(context_lines)
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve context for {job_id}: {e}")
            return "Context retrieval failed."
