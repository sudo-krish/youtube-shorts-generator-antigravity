import os
import time
import subprocess
import logging
import uuid
import ffmpeg

from .agents.observer import ObserverAgent
from .agents.scriptwriter import ScriptWriterAgent
from .agents.director import DirectorAgent
from .agents.editor import EditorAgent
from .agents.specialist import SpecialistAgent
from .agents.builder import BuilderAgent

from .tools.audio_hype import detect_audio_spikes
from .tools.ocr_reader import read_ocr_from_video
from .tools.web_scraper import fetch_regional_trends
from .tools.sfx_indexer import index_local_sfx
from .tools.math_validator import validate_editor_math
from pipeline.capabilities.effects.registry import get_capabilities_menu
from database import log_stage

logger = logging.getLogger(__name__)

WORKSPACE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "workspace")
os.makedirs(WORKSPACE_DIR, exist_ok=True)

class AIReviewer:
    """The multi-agent orchestrator that manages the N-Phase AI Assembly Line."""
    def __init__(self, video_path: str, metadata: dict = None):
        self.video_path = video_path
        self.metadata = metadata or {}
        self.observer = ObserverAgent()
        self.scriptwriter = ScriptWriterAgent()
        self.director = DirectorAgent()
        self.editor = EditorAgent()
        self.specialist = SpecialistAgent()
        self.builder = BuilderAgent()

    def split_video_with_overlap(self, input_path: str, job_id: str, chunk_duration: int = 900, overlap: int = 120):
        logger.info(f"Splitting video with overlap: {input_path}")
        probe = ffmpeg.probe(input_path)
        duration = float(probe['format']['duration'])
        
        chunks = []
        start = 0
        idx = 1
        
        while start < duration:
            end = min(start + chunk_duration, duration)
            current_duration = end - start
            
            chunk_name = f"{job_id}_chunk_{idx}.mp4"
            output_chunk_path = os.path.join(WORKSPACE_DIR, chunk_name)
            
            cmd = [
                "ffmpeg", "-y", "-i", input_path,
                "-ss", str(start), "-t", str(current_duration),
                "-c", "copy", output_chunk_path
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            chunks.append(output_chunk_path)
            
            if end >= duration:
                break
                
            start += chunk_duration - overlap
            idx += 1
            
        logger.info(f"Generated {len(chunks)} chunks.")
        return chunks

    def create_ai_proxy(self, input_mp4: str, job_id: str, job_logger: logging.Logger = logger) -> str:
        safe_name = str(uuid.uuid4())
        proxy_path = os.path.join(WORKSPACE_DIR, f"{job_id}_{safe_name}_proxy.mp4")
        
        job_logger.info(f"Generating lightweight AI Proxy for {os.path.basename(input_mp4)}...")
        cmd = [
            "ffmpeg", "-y", "-i", input_mp4,
            "-vf", "fps=1,scale=-2:480", 
            "-c:v", "libx264", "-crf", "35", "-preset", "ultrafast",
            "-an", proxy_path
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return proxy_path

    def run_multi_agent_pipeline(self, chunk_path: str, job_id: str, chunk_idx: int, resume_state: dict, job_logger: logging.Logger = logger):
        import google.genai as genai
        import json
        client = genai.Client()
        
        def get_state(step_name):
            return resume_state.get(f"chunk_{chunk_idx}_{step_name}")

        def save_state(step_name, data):
            if job_id:
                state_key = f"chunk_{chunk_idx}_{step_name}"
                log_stage(job_id, state_key, "completed", str(data))
                
                # Dedicated agent output file
                agents_dir = os.path.join(os.path.dirname(WORKSPACE_DIR), "outputs", "agents", job_id)
                os.makedirs(agents_dir, exist_ok=True)
                agent_file = os.path.join(agents_dir, f"{state_key}.txt")
                with open(agent_file, "w") as f:
                    if isinstance(data, str):
                        f.write(data)
                    else:
                        f.write(json.dumps(data, indent=2))

        uploaded_file = None
        proxy_path = None
        context = get_state("observer")
        
        # Only upload to Gemini if we actually need to run the Observer
        if not context:
            proxy_path = self.create_ai_proxy(chunk_path, job_id, job_logger)
            job_logger.info(f"Uploading AI proxy for {os.path.basename(chunk_path)}...")
            uploaded_file = client.files.upload(file=proxy_path)
            
            while True:
                file_info = client.files.get(name=uploaded_file.name)
                if file_info.state.name == "ACTIVE":
                    break
                elif file_info.state.name == "FAILED":
                    raise Exception("Video processing failed in Gemini API.")
                time.sleep(5)
            
        try:
            # Pre-generate Stage 1 Contexts (Observer)
            if not context:
                if job_id: log_stage(job_id, f"chunk_{chunk_idx}_observer", "running", "Generating Pre-Context: Audio Hype Map & OCR...")
                audio_spikes = detect_audio_spikes(chunk_path, top_n=5)
                ocr_dumps = read_ocr_from_video(chunk_path, audio_spikes)
            
            # Stage 1: Observer
            if not context:
                if job_id: log_stage(job_id, f"chunk_{chunk_idx}_observer", "running", "Observer Agent reading video context...")
                context = self.observer.execute(uploaded_file, self.metadata, audio_spikes, ocr_dumps)
                save_state("observer", context)
            
            # Pre-generate Stage 2 Contexts (Scriptwriter)
            web_trends = fetch_regional_trends(self.metadata.get("game_name", "Global"), self.metadata.get("region", "Global"))
            
            # Stage 2: Scriptwriter
            scripts = get_state("scriptwriter")
            if not scripts:
                if job_id: log_stage(job_id, f"chunk_{chunk_idx}_scriptwriter", "running", "Script Writer generating multi-variant templates...")
                scripts = self.scriptwriter.execute(context, self.metadata, web_trends)
                save_state("scriptwriter", scripts)
            
            # Pre-generate Stage 3 Contexts (Director)
            sfx_library = index_local_sfx()
            
            # Stage 3: Director
            vision = get_state("director")
            if not vision:
                if job_id: log_stage(job_id, f"chunk_{chunk_idx}_director", "running", "Director injecting magic and vibes...")
                vision = self.director.execute(scripts, self.metadata, sfx_library)
                save_state("director", vision)
            
            # Stage 4: Editor
            breakdown = get_state("editor")
            if not breakdown:
                if job_id: log_stage(job_id, f"chunk_{chunk_idx}_editor", "running", "Editor translating to FFmpeg technical capabilities...")
                breakdown = self.editor.execute(vision, self.metadata)
                save_state("editor", breakdown)
            
            # Pre-generate Stage 5 Contexts (Specialist)
            math_report = validate_editor_math(breakdown)
            rules_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "docs", "Architecture", "YOUTUBE_ALGORITHM_RULES.md")
            youtube_rules = ""
            if os.path.exists(rules_path):
                with open(rules_path, "r") as f:
                    youtube_rules = f.read()
            capabilities = get_capabilities_menu()
            
            # Stage 5: Specialist (YouTube Specialist & Final Polish Editor)
            validated_plans = get_state("specialist")
            if not validated_plans:
                if job_id: log_stage(job_id, f"chunk_{chunk_idx}_specialist", "running", "YouTube Specialist polishing technical plans for maximum algorithm retention...")
                validated_plans = self.specialist.execute(breakdown, self.metadata, math_report, youtube_rules, capabilities)
                save_state("specialist", validated_plans)
            
            # Stage 6: Builder
            if job_id: log_stage(job_id, f"chunk_{chunk_idx}_builder", "running", "Builder formatting finalized JSON blueprints...")
            json_output = self.builder.execute(validated_plans)
            
            return json_output.get("shorts", [])
            
        finally:
            try:
                if uploaded_file and hasattr(uploaded_file, 'name'):
                    client.files.delete(name=uploaded_file.name)
                if proxy_path and os.path.exists(proxy_path):
                    os.remove(proxy_path)
            except Exception as e:
                job_logger.warning(f"Error during cleanup: {e}")

    def review_video(self, job_id: str = None, resume_state: dict = None):
        job_logger = logging.getLogger(job_id) if job_id else logger
        
        # Configure file handler for this job if not already present
        if job_id and not any(isinstance(h, logging.FileHandler) for h in job_logger.handlers):
            log_dir = os.path.join(os.path.dirname(WORKSPACE_DIR), "outputs", "logs")
            os.makedirs(log_dir, exist_ok=True)
            fh = logging.FileHandler(os.path.join(log_dir, f"{job_id}.log"))
            fh.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            job_logger.addHandler(fh)
            job_logger.setLevel(logging.INFO)
            
        if resume_state is None:
            resume_state = {}
        try:
            chunk_duration = 900
            overlap = 120
            
            # Check if chunks already exist from a previous run
            chunks = []
            if job_id:
                existing = sorted([os.path.join(WORKSPACE_DIR, f) for f in os.listdir(WORKSPACE_DIR) if f.startswith(f"{job_id}_chunk_")])
                if existing:
                    job_logger.info(f"Found {len(existing)} existing chunks. Skipping chunk generation.")
                    chunks = existing
            
            if not chunks:
                if job_id: log_stage(job_id, "chunking", "running", "Splitting video into chunks (this may take a moment)...")
                chunks = self.split_video_with_overlap(self.video_path, job_id, chunk_duration, overlap)
                if job_id: log_stage(job_id, "chunking", "completed", f"Generated {len(chunks)} chunks.")
            
            all_shorts = []
            start_offset = 0
            
            for idx, chunk in enumerate(chunks):
                shorts = self.run_multi_agent_pipeline(chunk, job_id, idx, resume_state, job_logger)
                
                # Shift timestamps relative to whole VOD
                for short in shorts:
                    for phase in short.get("phases", []):
                        if "start_time" in phase: phase["start_time"] += start_offset
                        if "end_time" in phase: phase["end_time"] += start_offset
                            
                all_shorts.extend(shorts)
                
                if idx < len(chunks) - 1:
                    time.sleep(60)
                    
                start_offset += (chunk_duration - overlap)
                
            if job_id: log_stage(job_id, "finalizing", "running", "Finalizing N-Phase timeline...")
            
            final_timeline = {"shorts": all_shorts}
            
            if job_id: log_stage(job_id, "finalizing", "completed", str(final_timeline))
                
            # Cleanup only on success
            for chunk in chunks:
                if os.path.exists(chunk):
                    os.remove(chunk)
                
            return final_timeline
            
        except Exception as e:
            job_logger.error(f"Multi-Agent AI Specialist failed: {str(e)}")
            if job_id:
                log_stage(job_id, "failed", "failed", f"Failed: {str(e)}")
            raise e
