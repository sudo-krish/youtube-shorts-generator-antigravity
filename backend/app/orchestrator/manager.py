import os
import subprocess
import logging
import uuid
import ffmpeg

from app.agents.manager import (
    ObserverAgent, ScriptWriterAgent, DirectorAgent,
    EditorAgent, SpecialistAgent, BuilderAgent
)

from app.tools.manager import (
    detect_audio_spikes, read_ocr_from_video, fetch_regional_trends,
    index_local_sfx, index_local_music, validate_editor_math
)
from app.generator.capabilities.effects.registry import get_capabilities_menu
from core.db.manager import db

logger = logging.getLogger(__name__)

WORKSPACE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "workspace"
)
os.makedirs(WORKSPACE_DIR, exist_ok=True)


class AIOrchestrator:
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

    def split_video_with_overlap(
        self,
        input_path: str,
        job_id: str,
        chunk_duration: int = 900,
        overlap: int = 120,
    ):
        logger.info(f"Splitting video with overlap: {input_path}")
        probe = ffmpeg.probe(input_path)
        duration = float(probe["format"]["duration"])

        chunks = []
        start = 0
        idx = 1

        while start < duration:
            end = min(start + chunk_duration, duration)
            current_duration = end - start

            chunk_name = f"{job_id}_chunk_{idx}.mp4"
            output_chunk_path = os.path.join(WORKSPACE_DIR, chunk_name)

            cmd = [
                "ffmpeg",
                "-y",
                "-i",
                input_path,
                "-ss",
                str(start),
                "-t",
                str(current_duration),
                "-c",
                "copy",
                output_chunk_path,
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            chunks.append(output_chunk_path)

            if end >= duration:
                break

            start += chunk_duration - overlap
            idx += 1

        logger.info(f"Generated {len(chunks)} chunks.")
        return chunks


    def run_multi_agent_pipeline(
        self,
        chunk_path: str,
        job_id: str,
        chunk_idx: int,
        resume_state: dict,
        job_logger: logging.Logger = logger,
    ):
        import json

        did_work = False

        def get_state(step_name):
            return resume_state.get(chunk_idx, {}).get(step_name)

        def save_state(step_name, data, model_id=None):
            nonlocal did_work
            did_work = True
            if job_id:
                db.jobs.db.jobs.log_stage(job_id, step_name, "completed", str(data), chunk_id=chunk_idx, model_id=model_id)
                agents_dir = os.path.join(
                    os.path.dirname(WORKSPACE_DIR),
                    "outputs",
                    "agents",
                    job_id,
                    str(chunk_idx),
                )
                os.makedirs(agents_dir, exist_ok=True)
                with open(os.path.join(agents_dir, f"{step_name}.txt"), "w") as f:
                    f.write(
                        data if isinstance(data, str) else json.dumps(data, indent=2)
                    )

        def execute_stage(step_name, running_msg, action_fn, *args):
            state = get_state(step_name)
            if state:
                return state
                
            model_id = None
            try:
                from ai_director.config_manager import get_config
                config_models = get_config().get("models", {})
                if step_name in config_models:
                    model_str = config_models[step_name]
                    provider = "gemini" if "gemini" in model_str.lower() else "deepseek"
                    model_id = db.models.get_or_create(provider, model_str)
            except Exception as e:
                logger.warning(f"Could not determine model for stage {step_name}: {e}")

            if job_id:
                db.jobs.db.jobs.log_stage(job_id, step_name, "running", running_msg, chunk_id=chunk_idx, model_id=model_id)

            result = action_fn(*args)
            save_state(step_name, result, model_id)
            return result

        try:
            # Pre-Context (Only re-run if observer isn't cached)
            if not get_state("observer"):
                audio_spikes = detect_audio_spikes(chunk_path, top_n=5)
                ocr_dumps = read_ocr_from_video(chunk_path, audio_spikes)
            else:
                audio_spikes, ocr_dumps = [], {}

            # Transformers (Local Models mapped to stages)
            from app.transformers.manager import SemanticMatrixBuilder
            
            game_id = self.metadata.get("game_id")
            builder = SemanticMatrixBuilder(chunk_path, game_id=game_id)
            
            audio_matrix = execute_stage(
                "voxtral_audio",
                "Voxtral-Mini-3B extracting contextual audio events...",
                builder.build_audio_matrix,
                2
            )
            visual_matrix = execute_stage(
                "llava_transformer",
                "Llava Video Model generating rich frame descriptions...",
                builder.build_visual_matrix,
                3
            )
            spatial_matrix = execute_stage(
                "spatial_transformer",
                "Optical Flow calculating dense spatial movement...",
                builder.build_spatial_matrix,
                3
            )
            yolo_tracking = execute_stage(
                "yolo_tracking",
                "YOLO extracting player focus points...",
                builder.build_yolo_matrix,
                1
            )
            
            semantic_matrix = execute_stage(
                "matrix_merging",
                "Concatenating and merging Transformer Timelines...",
                builder.merge_matrices,
                audio_matrix,
                visual_matrix,
                spatial_matrix
            )

            context = execute_stage(
                "observer",
                "Observer Agent reading Semantic Matrix...",
                self.observer.execute,
                chunk_path,
                self.metadata,
                audio_spikes,
                ocr_dumps,
                semantic_matrix
            )

            # Stage 2: Scriptwriter
            web_trends = (
                fetch_regional_trends(
                    self.metadata.get("game_name", "Global"),
                    self.metadata.get("region", "Global"),
                )
                if not get_state("scriptwriter")
                else ""
            )

            scripts = execute_stage(
                "scriptwriter",
                "Script Writer generating multi-variant templates...",
                self.scriptwriter.execute,
                context,
                self.metadata,
                web_trends
            )

            # Stage 3: Director
            sfx_library = index_local_sfx() if not get_state("director") else ""
            music_library = index_local_music() if not get_state("director") else ""

            vision = execute_stage(
                "director",
                "Director injecting magic and vibes based on scripts...",
                self.director.execute,
                context,
                scripts,
                self.metadata,
                sfx_library,
                music_library
            )

            # Stage 4: Editor
            breakdown = execute_stage(
                "editor",
                "Editor translating to FFmpeg technical capabilities...",
                self.editor.execute,
                scripts,
                vision,
                self.metadata,
                yolo_tracking
            )

            # Stage 5: Specialist (YouTube Specialist & Final Polish Editor)
            if not get_state("specialist"):
                math_report = validate_editor_math(breakdown)
                rules_path = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    "docs",
                    "Rules",
                    "YOUTUBE_ALGORITHM_RULES.md",
                )
                youtube_rules = ""
                if os.path.exists(rules_path):
                    with open(rules_path, "r") as f:
                        youtube_rules = f.read()
                capabilities = get_capabilities_menu()
            else:
                math_report, youtube_rules, capabilities = "", "", ""

            validated_plans = execute_stage(
                "specialist",
                "YouTube Specialist polishing technical plans for maximum algorithm retention...",
                self.specialist.execute,
                breakdown,
                self.metadata,
                math_report,
                youtube_rules,
                capabilities
            )

            # Stage 6: Builder
            json_output = execute_stage(
                "builder",
                "Builder formatting finalized JSON blueprints...",
                self.builder.execute,
                validated_plans,
                self.metadata
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

            # Generate or Retrieve Chunks
            import ffmpeg
            from app.chunking.manager import get_or_create_chunk
            
            try:
                probe = ffmpeg.probe(self.video_path)
                total_duration = float(probe["format"]["duration"])
            except Exception as e:
                job_logger.error(f"Failed to probe video duration: {e}")
                raise e
            
            num_chunks = int((total_duration // chunk_duration) + 1)
            chunks = []
            
            if job_id:
                db.jobs.log_stage(
                    job_id,
                    "chunking",
                    "running",
                    f"Validating {num_chunks} chunks...",
                    chunk_id=None,
                )
                
            row = db.videos.get_by_path(self.video_path)
            video_id = row["video_id"] if row else "unknown_video"

            for i in range(num_chunks):
                chunk_path, _ = get_or_create_chunk(video_id, i, self.video_path, chunk_duration=chunk_duration)
                chunks.append(chunk_path)

            if job_id:
                db.jobs.update_status(job_id, "processing", num_chunks=num_chunks)
                db.jobs.log_stage(
                    job_id,
                    "chunking",
                    "completed",
                    f"Validated {len(chunks)} chunks.",
                    chunk_id=None,
                )

            all_shorts = []
            start_offset = 0

            for idx, chunk in enumerate(chunks):
                try:
                    shorts, did_work = self.run_multi_agent_pipeline(
                        chunk, job_id, idx, resume_state, job_logger
                    )

                    # Shift timestamps relative to whole VOD
                    for short in shorts:
                        for phase in short.get("phases", []):
                            if "start_time" in phase:
                                phase["start_time"] += start_offset
                            if "end_time" in phase:
                                phase["end_time"] += start_offset

                    all_shorts.extend(shorts)

                    if idx < len(chunks) - 1 and did_work:
                        job_logger.info(
                            f"Chunk {idx} completed processing. LLMClient will handle dynamic backoff if required."
                        )

                    start_offset += chunk_duration - overlap
                except Exception as chunk_e:
                    raise chunk_e

            if job_id:
                db.jobs.log_stage(
                    job_id,
                    "finalizing",
                    "running",
                    "Finalizing N-Phase timeline...",
                    chunk_id=None,
                )

            final_timeline = {"shorts": all_shorts}

            if job_id:
                db.jobs.log_stage(
                    job_id,
                    "finalizing",
                    "completed",
                    str(final_timeline),
                    chunk_id=None,
                )

            return final_timeline

        except Exception as e:
            job_logger.error(f"Multi-Agent AI Pipeline failed: {str(e)}")
            raise e
