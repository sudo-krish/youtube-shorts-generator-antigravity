import json
import time
from core.db.manager import db
from modules.orchestrator.schema import Job, JobStage, JobRender
from modules.media.editor.schema import Video
from sqlalchemy import select, insert, update

class OrchestratorService:
    @staticmethod
    def create_job(job_id: str, video_id: str, metadata: dict = None):
        db.create(Job, job_id=job_id, video_id=video_id, status="processing", 
                  metadata=json.dumps(metadata or {}), created_at=time.time())

    @staticmethod
    def update_job_status(job_id: str, status: str, json_path: str = None, num_chunks: int = None):
        updates = {"status": status}
        if json_path is not None: updates["json_path"] = json_path
        if num_chunks is not None: updates["num_chunks"] = num_chunks
        db.update(Job, filters={"job_id": job_id}, updates=updates)

    @staticmethod
    def get_job(job_id: str) -> dict:
        # Complex join for job + video, falling back to SQLAlchemy session for complex queries
        job_table = db.get_table(Job)
        vid_table = db.get_table(Video)
        
        with next(db.get_session()) as session:
            stmt = select(
                job_table.c.job_id, job_table.c.status, job_table.c.created_at, 
                vid_table.c.video_name, vid_table.c.video_path, job_table.c.json_path, 
                job_table.c.metadata, job_table.c.num_chunks, job_table.c.video_id
            ).select_from(
                job_table.join(vid_table, job_table.c.video_id == vid_table.c.video_id)
            ).where(job_table.c.job_id == job_id)
            
            row = session.execute(stmt).fetchone()
            if row:
                d = dict(row._mapping)
                try: d["metadata"] = json.loads(d.get("metadata") or "{}")
                except: d["metadata"] = {}
                return d
        return None

    @staticmethod
    def get_all_jobs() -> list:
        job_table = db.get_table(Job)
        vid_table = db.get_table(Video)
        
        with next(db.get_session()) as session:
            stmt = select(
                job_table.c.job_id, job_table.c.status, job_table.c.created_at, 
                vid_table.c.video_name, vid_table.c.video_path, job_table.c.json_path
            ).select_from(
                job_table.join(vid_table, job_table.c.video_id == vid_table.c.video_id)
            ).order_by(job_table.c.created_at.desc())
            
            return [dict(r._mapping) for r in session.execute(stmt).fetchall()]

    @staticmethod
    def log_stage(job_id: str, stage_name: str, status: str, logs: str = None, chunk_id: int = None, model_id: int = None):
        stages = db.filter(JobStage, job_id=job_id, stage_name=stage_name, chunk_id=chunk_id)
        current_time = time.time()
        end_time = current_time if status in ["completed", "failed"] else None
        
        if stages:
            stage_id = stages[0]["id"]
            updates = {"status": status, "logs": logs, "end_time": end_time}
            if model_id is not None: updates["model_id"] = model_id
            db.update(JobStage, filters={"id": stage_id}, updates=updates)
        else:
            db.create(JobStage, job_id=job_id, stage_name=stage_name, status=status, 
                      logs=logs, start_time=current_time, end_time=end_time, 
                      chunk_id=chunk_id, model_id=model_id)

    @staticmethod
    def fail_running_stages(job_id: str):
        stage_table = db.get_table(JobStage)
        with next(db.get_session()) as session:
            stmt = update(stage_table).where(
                (stage_table.c.job_id == job_id) & (stage_table.c.status.in_(["running", "processing"]))
            ).values(status="failed", end_time=time.time())
            session.execute(stmt)
            session.commit()

    @staticmethod
    def get_stages(job_id: str) -> dict:
        stages_data = db.filter(JobStage, order_by="start_time", descending=False, job_id=job_id)
        stages = {}
        for row in stages_data:
            key = row["stage_name"]
            if row["chunk_id"] is not None:
                key = f"chunk_{row['chunk_id']}_{row['stage_name']}"
            stages[key] = {
                "status": row["status"],
                "logs": row["logs"],
                "start_time": row["start_time"],
                "end_time": row["end_time"],
                "timestamp": row["start_time"]
            }
        return stages

    @staticmethod
    def get_completed_stages(job_id: str) -> list:
        return db.filter(JobStage, job_id=job_id, status="completed")

    @staticmethod
    def queue_render(task_id: str, job_id: str, variant_id: str):
        existing = db.get(JobRender, id=task_id)
        if not existing:
            now = time.time()
            db.create(JobRender, id=task_id, job_id=job_id, variant_id=variant_id, 
                      status="queued", error_logs="", created_at=now, updated_at=now)

    @staticmethod
    def update_render(task_id: str, status: str, error_logs: str = "", outputs: list = None):
        updates = {"status": status, "error_logs": error_logs, "updated_at": time.time()}
        if outputs is not None:
            updates["outputs"] = json.dumps(outputs)
        db.update(JobRender, filters={"id": task_id}, updates=updates)

    @staticmethod
    def get_renders(job_id: str) -> list:
        renders = db.filter(JobRender, job_id=job_id)
        for r in renders:
            try: r["outputs"] = json.loads(r["outputs"]) if r["outputs"] else []
            except: r["outputs"] = []
        return renders

orchestrator_service = OrchestratorService()
