from core.file_manager import file_manager
from pathlib import Path
import subprocess
import logging
import json
import httpx
from modules.jobs.service import job_service

logger = logging.getLogger(__name__)

class AIOrchestratorStateMachine:
    """The multi-agent orchestrator that manages the N-Phase AI Assembly Line via Nano-Services."""

    def __init__(self, video_path: str, metadata: dict = None, base_url: str = "http://localhost:8000"):
        self.video_path = video_path
        self.metadata = metadata or {}
        self.base_url = base_url
        self.client = httpx.Client(timeout=300.0)

    def _call_nano_service(self, endpoint: str, payload: dict) -> dict:
        url = f"{self.base_url}{endpoint}"
        logger.info(f"Triggering Nano-Service: {url}")
        response = self.client.post(url, json={"payload": payload})
        response.raise_for_status()
        return response.json().get("output", {})

    def resolve_params(self, params: dict, context: dict) -> dict:
        """Resolve dynamic parameters like $step_name.key from the context."""
        resolved = {}
        for k, v in params.items():
            if isinstance(v, str) and v.startswith("$"):
                # e.g., $narrator.action_log
                parts = v[1:].split(".")
                if len(parts) == 2:
                    step_name, key = parts
                    resolved[k] = context.get(step_name, {}).get(key, "")
                else:
                    resolved[k] = context.get(parts[0], "")
            else:
                resolved[k] = v
        return resolved

    def run_dynamic_pipeline(
        self,
        sequence: list,
        chunk_path: str,
        job_id: str,
        chunk_idx: int,
        resume_state: dict,
        job_logger: logging.Logger = logger,
    ):
        did_work = False
        context = {"global": {"video_path": chunk_path, "metadata": self.metadata, "job_id": job_id}}

        def get_state(step_name):
            return resume_state.get(chunk_idx, {}).get(step_name)

        def save_state(step_name, data):
            nonlocal did_work
            did_work = True
            if job_id:
                job_service.log_stage(job_id, step_name, "completed", str(data), chunk_id=chunk_idx)
                
                # Use file manager to save agent output state
                if isinstance(data, dict):
                    file_manager.write_json("agent_output", f"{job_id}/chunk_{chunk_idx}_{step_name}.json", data)
                else:
                    file_manager.write_text("agent_output", f"{job_id}/chunk_{chunk_idx}_{step_name}.json", str(data))

        def execute_stage(step_name, endpoint, payload):
            state = get_state(step_name)
            if state:
                if isinstance(state, str):
                    try:
                        state = json.loads(state)
                    except:
                        pass
                return state
                
            if job_id:
                job_service.log_stage(job_id, step_name, "running", f"Running {step_name}...", chunk_id=chunk_idx)

            result = self._call_nano_service(endpoint, payload)
            save_state(step_name, result)
            return result

        try:
            last_result = None
            for step in sequence:
                step_name = step.get("name")
                endpoint = step.get("endpoint")
                raw_params = step.get("params", {})
                
                # Resolve any dynamic dependencies using the context
                payload = self.resolve_params(raw_params, context)
                # Inject global variables if needed
                if "metadata" not in payload:
                    payload["metadata"] = self.metadata
                if "job_id" not in payload:
                    payload["job_id"] = job_id
                
                result = execute_stage(step_name, endpoint, payload)
                # Save result to context for future steps to reference
                context[step_name] = result if isinstance(result, dict) else {"output": result}
                last_result = result

            # Attempt to extract shorts from the final result
            if isinstance(last_result, list):
                shorts = last_result
            elif isinstance(last_result, dict):
                shorts = last_result.get("shorts", [])
            else:
                shorts = []
                
            return shorts, did_work

        finally:
            pass

    def get_default_sequence(self):
        return [
            {
                "name": "narrator", 
                "endpoint": "/api/ai/agents/narrator", 
                "params": {"frame_dir": f"/tmp/frames"}
            },
            {
                "name": "scriptwriter", 
                "endpoint": "/api/ai/agents/scriptwriter", 
                "params": {"observer_context": "$narrator.action_log", "web_trends": ""}
            },
            {
                "name": "director", 
                "endpoint": "/api/ai/agents/director", 
                "params": {"observer_context": "$narrator.action_log", "scripts": "$scriptwriter.scripts", "sfx_library": "", "music_library": ""}
            },
            {
                "name": "editor", 
                "endpoint": "/api/ai/agents/editor", 
                "params": {"scripts_context": "$scriptwriter.scripts", "director_vision": "$director.director_rules"}
            },
            {
                "name": "specialist", 
                "endpoint": "/api/ai/agents/specialist", 
                "params": {"editor_breakdown": "$editor.technical_directives", "math_report": "", "youtube_rules": "", "capabilities": ""}
            },
            {
                "name": "builder", 
                "endpoint": "/api/ai/agents/builder", 
                "params": {"validated_breakdown": "$specialist.polished_breakdown"}
            }
        ]

    def orchestrate_pipeline(self, job_id: str = None, resume_state: dict = None, sequence: list = None):
        job_logger = logging.getLogger("ai_director")

        if resume_state is None:
            resume_state = {}
            
        if not sequence:
            sequence = self.get_default_sequence()
            
        try:
            chunk_duration = 900
            overlap = 120
            
            chunks = [self.video_path]
            all_shorts = []
            start_offset = 0

            for idx, chunk in enumerate(chunks):
                shorts, did_work = self.run_dynamic_pipeline(sequence, chunk, job_id, idx, resume_state, job_logger)

                for short in shorts:
                    if isinstance(short, dict):
                        for phase in short.get("phases", []):
                            if "start_time" in phase:
                                phase["start_time"] += start_offset
                            if "end_time" in phase:
                                phase["end_time"] += start_offset

                all_shorts.extend(shorts)
                start_offset += chunk_duration - overlap

            return {"shorts": all_shorts}

        except Exception as e:
            job_logger.error(f"Multi-Agent AI Pipeline failed: {str(e)}")
            raise e
