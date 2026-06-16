import json
import time
from .connection import execute_read_query, execute_read_one, execute_write_query

class VideoManager:
    def create(self, video_id: str, video_name: str, video_path: str):
        query = "INSERT INTO videos (video_id, video_name, video_path, created_at) VALUES (?, ?, ?, ?)"
        execute_write_query(query, (video_id, video_name, video_path, time.time()))

    def get(self, video_id: str) -> dict:
        return execute_read_one("SELECT * FROM videos WHERE video_id = ?", (video_id,))
        
    def get_by_path(self, video_path: str) -> dict:
        return execute_read_one("SELECT * FROM videos WHERE video_path = ?", (video_path,))

    def get_all(self) -> list:
        return execute_read_query("SELECT * FROM videos ORDER BY created_at DESC")

class ChunkManager:
    def get_by_index(self, video_id: str, chunk_index: int) -> dict:
        # Fallback logic for audio_chunk_name is handled by DB ALTERs now.
        return execute_read_one(
            "SELECT chunk_id, chunk_name, audio_chunk_name, start_time, end_time FROM video_chunks WHERE video_id = ? AND chunk_index = ?", 
            (video_id, chunk_index)
        )

    def create(self, chunk_id: str, video_id: str, chunk_index: int, chunk_name: str, audio_chunk_name: str, start_time: float, duration: float):
        query = "INSERT INTO video_chunks (chunk_id, video_id, chunk_index, chunk_name, audio_chunk_name, start_time, end_time) VALUES (?, ?, ?, ?, ?, ?, ?)"
        execute_write_query(query, (chunk_id, video_id, chunk_index, chunk_name, audio_chunk_name, start_time, start_time + duration))

    def update_audio_name(self, chunk_id: str, audio_chunk_name: str):
        execute_write_query("UPDATE video_chunks SET audio_chunk_name = ? WHERE chunk_id = ?", (audio_chunk_name, chunk_id))

    def delete(self, chunk_id: str):
        execute_write_query("DELETE FROM video_chunks WHERE chunk_id = ?", (chunk_id,))

class JobManager:
    def create(self, job_id: str, video_id: str, metadata: dict = None):
        query = "INSERT INTO jobs (job_id, video_id, status, metadata, created_at, json_path) VALUES (?, ?, ?, ?, ?, ?)"
        execute_write_query(query, (job_id, video_id, "processing", json.dumps(metadata or {}), time.time(), None))

    def update_status(self, job_id: str, status: str, json_path: str = None, num_chunks: int = None):
        updates = ["status = ?"]
        params = [status]

        if json_path:
            updates.append("json_path = ?")
            params.append(json_path)
        if num_chunks is not None:
            updates.append("num_chunks = ?")
            params.append(num_chunks)

        params.append(job_id)
        query = f"UPDATE jobs SET {', '.join(updates)} WHERE job_id = ?"
        execute_write_query(query, tuple(params))

    def get(self, job_id: str) -> dict:
        query = """
        SELECT j.job_id, j.status, j.created_at, v.video_name, v.video_path, j.json_path, j.metadata, j.num_chunks, j.video_id
        FROM jobs j JOIN videos v ON j.video_id = v.video_id WHERE j.job_id = ?
        """
        job_dict = execute_read_one(query, (job_id,))
        if job_dict:
            try: job_dict["metadata"] = json.loads(job_dict.get("metadata") or "{}")
            except: job_dict["metadata"] = {}
        return job_dict

    def get_all(self):
        query = """
        SELECT j.job_id, j.status, j.created_at, v.video_name, v.video_path, j.json_path
        FROM jobs j JOIN videos v ON j.video_id = v.video_id ORDER BY j.created_at DESC
        """
        return execute_read_query(query)

    def log_stage(self, job_id: str, stage_name: str, status: str, logs: str = None, chunk_id: int = None, model_id: int = None):
        if chunk_id is not None:
            row = execute_read_one("SELECT id, start_time FROM job_stages WHERE job_id = ? AND stage_name = ? AND chunk_id = ?", (job_id, stage_name, chunk_id))
        else:
            row = execute_read_one("SELECT id, start_time FROM job_stages WHERE job_id = ? AND stage_name = ? AND chunk_id IS NULL", (job_id, stage_name))

        current_time = time.time()
        end_time = current_time if status in ["completed", "failed"] else None

        if row:
            updates = ["status = ?", "logs = ?", "end_time = ?"]
            params = [status, logs, end_time]
            if model_id is not None:
                updates.append("model_id = ?")
                params.append(model_id)
            params.append(row["id"])
            execute_write_query(f"UPDATE job_stages SET {', '.join(updates)} WHERE id = ?", tuple(params))
        else:
            query = "INSERT INTO job_stages (job_id, stage_name, status, logs, start_time, end_time, chunk_id, model_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
            execute_write_query(query, (job_id, stage_name, status, logs, current_time, end_time, chunk_id, model_id))

    def fail_running_stages(self, job_id: str):
        query = "UPDATE job_stages SET status = 'failed', end_time = ? WHERE job_id = ? AND status IN ('running', 'processing')"
        execute_write_query(query, (time.time(), job_id))

    def get_stages(self, job_id: str) -> dict:
        rows = execute_read_query("SELECT stage_name, chunk_id, status, logs, start_time, end_time FROM job_stages WHERE job_id = ? ORDER BY start_time ASC", (job_id,))
        stages = {}
        for row in rows:
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

    def get_completed_stages(self, job_id: str) -> list:
        return execute_read_query('SELECT chunk_id, stage_name, logs FROM job_stages WHERE job_id = ? AND status = "completed"', (job_id,))

    def queue_render(self, task_id: str, job_id: str, variant_id: str):
        now = time.time()
        execute_write_query("INSERT OR IGNORE INTO job_renders (id, job_id, variant_id, status, error_logs, created_at, updated_at) VALUES (?, ?, ?, 'queued', '', ?, ?)", (task_id, job_id, variant_id, now, now))

    def update_render(self, task_id: str, status: str, error_logs: str = "", outputs: list = None):
        if outputs is not None:
            outputs_str = json.dumps(outputs)
            execute_write_query("UPDATE job_renders SET status = ?, error_logs = ?, outputs = ?, updated_at = ? WHERE id = ?", (status, error_logs, outputs_str, time.time(), task_id))
        else:
            execute_write_query("UPDATE job_renders SET status = ?, error_logs = ?, updated_at = ? WHERE id = ?", (status, error_logs, time.time(), task_id))

    def get_renders(self, job_id: str) -> list:
        rows = execute_read_query("SELECT variant_id, status, error_logs, outputs FROM job_renders WHERE job_id = ?", (job_id,))
        results = []
        for d in rows:
            try: d["outputs"] = json.loads(d["outputs"]) if d["outputs"] else []
            except: d["outputs"] = []
            results.append(d)
        return results

class TestManager:
    def create(self, test_id: str, video_id: str, chunk_index: int, transformer_name: str):
        query = "INSERT INTO transformer_tests (test_id, video_id, chunk_index, transformer_name, status, start_time) VALUES (?, ?, ?, ?, 'running', ?)"
        execute_write_query(query, (test_id, video_id, chunk_index, transformer_name, time.time()))

    def update(self, test_id: str, status: str, output_data: str = None, visual_path: str = None):
        if status == 'completed':
            query = "UPDATE transformer_tests SET status = ?, end_time = ?, output_data = ?, visual_output_path = ? WHERE test_id = ?"
            execute_write_query(query, (status, time.time(), output_data, visual_path, test_id))
        else:
            query = "UPDATE transformer_tests SET status = ?, end_time = ?, output_data = ? WHERE test_id = ?"
            execute_write_query(query, (status, time.time(), output_data, test_id))

    def get_all(self):
        return execute_read_query("SELECT test_id, video_id, chunk_index, transformer_name, status, start_time, end_time, output_data, visual_output_path FROM transformer_tests ORDER BY start_time DESC")

class DBManager:
    def __init__(self):
        self.videos = VideoManager()
        self.chunks = ChunkManager()
        self.jobs = JobManager()
        self.tests = TestManager()
        self.models = ModelManager()
        self.games = GameManager()

    def clear_all(self):
        execute_write_query("DELETE FROM job_stages")
        execute_write_query("DELETE FROM jobs")
        execute_write_query("DELETE FROM videos")
        execute_write_query("DELETE FROM transformer_tests")
        execute_write_query("DELETE FROM video_chunks")
        execute_write_query("DELETE FROM job_renders")

    def get_database_dump(self):
        dump = {}
        tables = ["videos", "video_chunks", "transformer_tests", "jobs", "job_stages", "models", "model_usage", "rate_limits", "job_renders", "dim_game_types", "dim_games", "audio_keywords"]
        for table in tables:
            rows = execute_read_query(f"SELECT * FROM {table}")
            if table == "jobs":
                for j in rows:
                    try: j["metadata"] = json.loads(j.get("metadata") or "{}")
                    except: j["metadata"] = {}
            dump[table] = rows
        return dump



class ModelManager:
    def get_or_create(self, provider: str, model_name: str) -> int:
        row = execute_read_one("SELECT id FROM models WHERE model_name = ?", (model_name,))
        if row: return row["id"]
        return execute_write_query("INSERT INTO models (provider, model_name) VALUES (?, ?)", (provider, model_name))

    def log_usage(self, model_id: int, prompt_tokens: int, completion_tokens: int, cost: float):
        execute_write_query("INSERT INTO model_usage (model_id, prompt_tokens, completion_tokens, cost, timestamp) VALUES (?, ?, ?, ?, ?)", (model_id, prompt_tokens, completion_tokens, cost, time.time()))

    def log_rate_limit(self, model_id: int, error_message: str):
        execute_write_query("INSERT INTO rate_limits (model_id, timestamp, error_message) VALUES (?, ?, ?)", (model_id, time.time(), error_message))

    def get_metrics_summary(self) -> dict:
        usage_data = execute_read_query("""
            SELECT m.provider, m.model_name, SUM(u.prompt_tokens) as total_prompt_tokens, SUM(u.completion_tokens) as total_completion_tokens, SUM(u.cost) as total_cost, COUNT(u.id) as total_requests
            FROM models m LEFT JOIN model_usage u ON m.id = u.model_id GROUP BY m.id
        """)
        rate_limits = execute_read_query("""
            SELECT m.model_name, r.timestamp, r.error_message
            FROM rate_limits r JOIN models m ON r.model_id = m.id ORDER BY r.timestamp DESC LIMIT 50
        """)
        return {"usage": usage_data, "rate_limits": rate_limits}

class GameManager:
    def get_supported_games(self) -> list:
        return execute_read_query('''
            SELECT g.id, g.game_name, t.game_genre, t.id as game_type_id, g.folder_path
            FROM dim_games g JOIN dim_game_types t ON g.game_type_id = t.id ORDER BY g.game_name ASC
        ''')

    def get_game_types(self) -> list:
        return execute_read_query('SELECT id, game_genre FROM dim_game_types ORDER BY game_genre ASC')

    def get_audio_keywords(self, game_id: int) -> list:
        rows = execute_read_query('''
            SELECT k.keyword FROM audio_keywords k JOIN dim_games g ON g.game_type_id = k.game_type_id WHERE g.id = ?
        ''', (game_id,))
        return [r["keyword"] for r in rows]

    def get_game_context_path(self, game_id: int) -> str:
        row = execute_read_one('SELECT folder_path FROM dim_games WHERE id = ?', (game_id,))
        if row:
            return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), row["folder_path"], 'context.txt')
        return None

    def create_game(self, game_name: str, game_type_id: int):
        game_uuid = str(uuid.uuid4())
        folder_path = os.path.join("assets", "games", game_uuid)
        abs_folder_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), folder_path)
        os.makedirs(abs_folder_path, exist_ok=True)
        with open(os.path.join(abs_folder_path, "context.txt"), "w") as f:
            f.write(f"Context and lore for {game_name}.\\n")
        execute_write_query("INSERT INTO dim_games (game_type_id, game_name, folder_path) VALUES (?, ?, ?)", (game_type_id, game_name, folder_path))

db = DBManager()
