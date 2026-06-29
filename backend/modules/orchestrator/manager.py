from core.file_manager import file_manager
from pathlib import Path
import subprocess
import logging
import json
import httpx
from modules.orchestrator.service import orchestrator_service
from core.settings import AGENTS_OUTPUT_DIR

logger = logging.getLogger(__name__)

ASSETS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "assets"
)
os.makedirs(ASSETS_DIR, exist_ok=True)

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

    def run_multi_agent_pipeline(
        self,
        chunk_path: str,
        job_id: str,
        chunk_idx: int,
        resume_state: dict,
        job_logger: logging.Logger = logger,
    ):
        did_work = False

        def get_state(step_name):
            return resume_state.get(chunk_idx, {}).get(step_name)

        def save_state(step_name, data):
            nonlocal did_work
            did_work = True
            if job_id:
                orchestrator_service.log_stage(job_id, step_name, "completed", str(data), chunk_id=chunk_idx)
                agents_dir = os.path.join(
                    os.path.dirname(ASSETS_DIR),
                    "outputs",
                    "agents",
                    job_id,
                    str(chunk_idx),
                )
                os.makedirs(agents_dir, exist_ok=True)
                with open(os.path.join(agents_dir, f"{step_name}.txt"), "w") as f:
                    f.write(data if isinstance(data, str) else json.dumps(data, indent=2))

        def execute_stage(step_name, running_msg, endpoint, payload):
            state = get_state(step_name)
            if state:
                return state
                
            if job_id:
                orchestrator_service.log_stage(job_id, step_name, "running", running_msg, chunk_id=chunk_idx)

            result = self._call_nano_service(endpoint, payload)
            save_state(step_name, result)
            return result

        try:
            # Note: Transformers are not fully migrated in Phase 3 yet, so we will stub their matrix generation.
            # In a full implementation, they would also be HTTP calls.
            semantic_matrix = [] # Stub for un-migrated transformers

            narrator_res = execute_stage(
                "narrator",
                "Narrator Agent watching video and extracting semantic context...",
                "/api/ai/agents/narrator",
                {
                    "job_id": job_id,
                    "frame_dir": f"/tmp/jobs/{job_id}/frames",
                    "metadata": self.metadata,
                }
            )
            context = narrator_res.get("action_log", "") if isinstance(narrator_res, dict) else narrator_res

            scripts_res = execute_stage(
                "scriptwriter",
                "Script Writer generating multi-variant templates...",
                "/api/ai/agents/scriptwriter",
                {
                    "observer_context": context,
                    "metadata": self.metadata,
                    "web_trends": ""
                }
            )
            scripts = scripts_res.get("scripts", "") if isinstance(scripts_res, dict) else scripts_res

            vision_res = execute_stage(
                "director",
                "Director injecting magic and vibes based on scripts...",
                "/api/ai/agents/director",
                {
                    "observer_context": context,
                    "scripts": scripts,
                    "metadata": self.metadata,
                    "sfx_library": "",
                    "music_library": ""
                }
            )
            vision = vision_res.get("director_rules", "") if isinstance(vision_res, dict) else vision_res

            breakdown_res = execute_stage(
                "editor",
                "Editor translating to FFmpeg technical capabilities...",
                "/api/ai/agents/editor",
                {
                    "scripts_context": scripts,
                    "director_vision": vision,
                    "metadata": self.metadata
                }
            )
            breakdown = breakdown_res.get("technical_directives", "") if isinstance(breakdown_res, dict) else breakdown_res

            validated_plans_res = execute_stage(
                "specialist",
                "YouTube Specialist polishing technical plans for maximum algorithm retention...",
                "/api/ai/agents/specialist",
                {
                    "editor_breakdown": breakdown,
                    "metadata": self.metadata,
                    "math_report": "",
                    "youtube_rules": "",
                    "capabilities": ""
                }
            )
            validated_plans = validated_plans_res.get("polished_breakdown", "") if isinstance(validated_plans_res, dict) else validated_plans_res

            json_output = execute_stage(
                "builder",
                "Builder formatting finalized JSON blueprints...",
                "/api/ai/agents/builder",
                {
                    "validated_breakdown": validated_plans
                }
            )

            if isinstance(json_output, list):
                shorts = json_output
            else:
                shorts = json_output.get("shorts", [])
                
            return shorts, did_work

        finally:
            pass

    def orchestrate_pipeline(self, job_id: str = None, resume_state: dict = None):
        job_logger = logging.getLogger("ai_director")

        if resume_state is None:
            resume_state = {}
        try:
            chunk_duration = 900
            overlap = 120
            
            # Skipping chunking for brevity in State Machine demo.
            chunks = [self.video_path]
            all_shorts = []
            start_offset = 0

            for idx, chunk in enumerate(chunks):
                shorts, did_work = self.run_multi_agent_pipeline(chunk, job_id, idx, resume_state, job_logger)

                for short in shorts:
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
