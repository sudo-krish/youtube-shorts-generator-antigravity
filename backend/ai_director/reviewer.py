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
from .tools.audio_indexer import index_local_music
from .tools.math_validator import validate_editor_math
from .tools.tracker import track_subject
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
            return resume_state.get(chunk_idx, {}).get(step_name)

        def save_state(step_name, data):
            nonlocal did_work
            did_work = True
            if job_id:
                log_stage(job_id, step_name, "completed", str(data), chunk_id=chunk_idx)
                
                # Dedicated agent output file
                agents_dir = os.path.join(os.path.dirname(WORKSPACE_DIR), "outputs", "agents", job_id, str(chunk_idx))
                os.makedirs(agents_dir, exist_ok=True)
                agent_file = os.path.join(agents_dir, f"{step_name}.txt")
                with open(agent_file, "w") as f:
                    if isinstance(data, str):
                        f.write(data)
                    else:
                        f.write(json.dumps(data, indent=2))

        uploaded_file = None
        proxy_path = None
        context = get_state("observer")
        did_work = False
        
        current_stage = "observer"
        
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
            # Stage 1: Observer
            if not context:
                if job_id: log_stage(job_id, "observer", "running", "Generating Pre-Context: AI Tracking, Audio Hype Map & OCR...", chunk_id=chunk_idx)
                audio_spikes = detect_audio_spikes(chunk_path, top_n=5)
                ocr_dumps = read_ocr_from_video(chunk_path, audio_spikes)
                tracking_data = track_subject(chunk_path, fps=1)
                
                if job_id: log_stage(job_id, "observer", "running", "Observer Agent reading video context...", chunk_id=chunk_idx)
                context = self.observer.execute(uploaded_file, self.metadata, audio_spikes, ocr_dumps, tracking_data)
                save_state("observer", context)
            
            current_stage = "scriptwriter"
            # Stage 2: Scriptwriter
            scripts = get_state("scriptwriter")
            if not scripts:
                web_trends = fetch_regional_trends(self.metadata.get("game_name", "Global"), self.metadata.get("region", "Global"))
                if job_id: log_stage(job_id, "scriptwriter", "running", "Script Writer generating multi-variant templates...", chunk_id=chunk_idx)
                scripts = self.scriptwriter.execute(context, self.metadata, web_trends)
                save_state("scriptwriter", scripts)
            
            current_stage = "director"
            # Stage 3: Director
            vision = get_state("director")
            if not vision:
                sfx_library = index_local_sfx()
                music_library = index_local_music()
                if job_id: log_stage(job_id, "director", "running", "Director injecting magic and vibes...", chunk_id=chunk_idx)
                vision = self.director.execute(scripts, self.metadata, sfx_library, music_library)
                save_state("director", vision)
            
            current_stage = "editor"
            # Stage 4: Editor
            breakdown = get_state("editor")
            if not breakdown:
                if job_id: log_stage(job_id, "editor", "running", "Editor translating to FFmpeg technical capabilities...", chunk_id=chunk_idx)
                breakdown = self.editor.execute(vision, self.metadata)
                save_state("editor", breakdown)
            
            current_stage = "specialist"
            # Stage 5: Specialist (YouTube Specialist & Final Polish Editor)
            validated_plans = get_state("specialist")
            if not validated_plans:
                math_report = validate_editor_math(breakdown)
                rules_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "docs", "Rules", "YOUTUBE_ALGORITHM_RULES.md")
                youtube_rules = ""
                if os.path.exists(rules_path):
                    with open(rules_path, "r") as f:
                        youtube_rules = f.read()
                capabilities = get_capabilities_menu()
                
                if job_id: log_stage(job_id, "specialist", "running", "YouTube Specialist polishing technical plans for maximum algorithm retention...", chunk_id=chunk_idx)
                validated_plans = self.specialist.execute(breakdown, self.metadata, math_report, youtube_rules, capabilities)
                save_state("specialist", validated_plans)
            
            current_stage = "builder"
            json_output = get_state("builder")
            if not json_output:
                if job_id: log_stage(job_id, "builder", "running", "Builder formatting finalized JSON blueprints...", chunk_id=chunk_idx)
                json_output = self.builder.execute(validated_plans)
                save_state("builder", json_output)
            
            return json_output.get("shorts", []), did_work
            
        finally:
            try:
                if uploaded_file and hasattr(uploaded_file, 'name'):
                    client.files.delete(name=uploaded_file.name)
                if proxy_path and os.path.exists(proxy_path):
                    os.remove(proxy_path)
            except Exception as e:
                job_logger.warning(f"Error during cleanup: {e}")

    def review_video(self, job_id: str = None, resume_state: dict = None):
        job_logger = logging.getLogger("ai_director")

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
                if job_id: log_stage(job_id, "chunking", "running", "Splitting video into chunks (this may take a moment)...", chunk_id=None)
                chunks = self.split_video_with_overlap(self.video_path, job_id, chunk_duration, overlap)
                if job_id:
                    from database import update_job_status
                    update_job_status(job_id, "processing", num_chunks=len(chunks))
                    log_stage(job_id, "chunking", "completed", f"Generated {len(chunks)} chunks.", chunk_id=None)
            
            all_shorts = []
            start_offset = 0
            
            for idx, chunk in enumerate(chunks):
                try:
                    shorts, did_work = self.run_multi_agent_pipeline(chunk, job_id, idx, resume_state, job_logger)
                    
                    # Shift timestamps relative to whole VOD
                    for short in shorts:
                        for phase in short.get("phases", []):
                            if "start_time" in phase: phase["start_time"] += start_offset
                            if "end_time" in phase: phase["end_time"] += start_offset
                                
                    all_shorts.extend(shorts)
                    
                    if idx < len(chunks) - 1 and did_work:
                        job_logger.info(f"Chunk {idx} completed processing. Sleeping 60s to respect API limits before next chunk...")
                        time.sleep(60)
                        
                    start_offset += (chunk_duration - overlap)
                except Exception as chunk_e:
                    # We catch here so we can fail the exact chunk_idx if it's bubbling up, though it's safer
                    # to just raise and let it be handled generally. main.py will mark all running as failed.
                    raise chunk_e
                
            if job_id: log_stage(job_id, "finalizing", "running", "Finalizing N-Phase timeline...", chunk_id=None)
            
            final_timeline = {"shorts": all_shorts}
            
            if job_id: log_stage(job_id, "finalizing", "completed", str(final_timeline), chunk_id=None)
                
            # Cleanup only on success
            for chunk in chunks:
                if os.path.exists(chunk):
                    os.remove(chunk)
                
            return final_timeline
            
        except Exception as e:
            job_logger.error(f"Multi-Agent AI Specialist failed: {str(e)}")
            # We don't log a generic failed stage anymore, because main.py will update any running stages to failed.
            raise e
