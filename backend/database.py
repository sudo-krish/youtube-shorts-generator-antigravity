import sqlite3
import os
import time
import json
import logging
import uuid

logger = logging.getLogger(__name__)
DB_PATH = os.path.join(os.path.dirname(__file__), "antigravity.db")

def get_db_connection():
    return sqlite3.connect(DB_PATH, timeout=15.0, check_same_thread=False)


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    
    # Create videos table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS videos (
        video_id TEXT PRIMARY KEY,
        video_name TEXT,
        video_path TEXT,
        created_at REAL
    )
    """)

    # Create jobs table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
        job_id TEXT PRIMARY KEY,
        video_id TEXT,
        status TEXT,
        created_at REAL,
        json_path TEXT,
        FOREIGN KEY (video_id) REFERENCES videos (video_id)
    )
    """)

    # Create job_stages table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS job_stages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id TEXT,
        stage_name TEXT,
        status TEXT,
        logs TEXT,
        start_time REAL,
        end_time REAL,
        chunk_id INTEGER,
        model_id INTEGER,
        FOREIGN KEY (job_id) REFERENCES jobs (job_id),
        FOREIGN KEY (model_id) REFERENCES models (id)
    )
    """)

    # Create models table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS models (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        provider TEXT,
        model_name TEXT UNIQUE
    )
    """)

    # Create model_usage table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS model_usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        model_id INTEGER,
        prompt_tokens INTEGER,
        completion_tokens INTEGER,
        cost REAL,
        timestamp REAL,
        FOREIGN KEY (model_id) REFERENCES models (id)
    )
    """)

    # Create rate_limits table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rate_limits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        model_id INTEGER,
        timestamp REAL,
        error_message TEXT,
        FOREIGN KEY (model_id) REFERENCES models (id)
    )
    """)

    # Create job_renders table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS job_renders (
        id TEXT PRIMARY KEY,
        job_id TEXT,
        variant_id TEXT,
        status TEXT,
        error_logs TEXT,
        outputs TEXT,
        created_at REAL,
        updated_at REAL,
        FOREIGN KEY (job_id) REFERENCES jobs (job_id)
    )
    """)

    try:
        cursor.execute("ALTER TABLE job_renders ADD COLUMN outputs TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE jobs ADD COLUMN metadata TEXT")
    except sqlite3.OperationalError:
        pass  # Column might already exist

    try:
        cursor.execute("ALTER TABLE jobs ADD COLUMN num_chunks INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE job_stages ADD COLUMN model_id INTEGER")
    except sqlite3.OperationalError:
        pass

    # Create Game Management Tables
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dim_game_types (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        game_genre TEXT UNIQUE
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dim_games (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        game_type_id INTEGER,
        game_name TEXT UNIQUE,
        folder_path TEXT,
        FOREIGN KEY (game_type_id) REFERENCES dim_game_types (id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audio_keywords (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        game_type_id INTEGER,
        keyword TEXT,
        FOREIGN KEY (game_type_id) REFERENCES dim_game_types (id)
    )
    """)
    
    seed_game_data(conn)

    conn.commit()
    conn.close()
    logger.info(f"Initialized database at {DB_PATH}")


def create_video(video_id: str, video_name: str, video_path: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
    INSERT INTO videos (video_id, video_name, video_path, created_at)
    VALUES (?, ?, ?, ?)
    """,
        (video_id, video_name, video_path, time.time()),
    )
    conn.commit()
    conn.close()


def get_video(video_id: str):
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM videos WHERE video_id = ?", (video_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def create_job(job_id: str, video_id: str, metadata: dict = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
    INSERT INTO jobs (job_id, video_id, status, metadata, created_at, json_path)
    VALUES (?, ?, ?, ?, ?, ?)
    """,
        (job_id, video_id, "processing", json.dumps(metadata or {}), time.time(), None),
    )
    conn.commit()
    conn.close()


def update_job_status(
    job_id: str, status: str, json_path: str = None, num_chunks: int = None
):
    conn = get_db_connection()
    cursor = conn.cursor()
    updates = ["status = ?"]
    params = [status]

    if json_path:
        updates.append("json_path = ?")
        params.append(json_path)
    if num_chunks is not None:
        updates.append("num_chunks = ?")
        params.append(num_chunks)

    params.append(job_id)

    cursor.execute(
        f"UPDATE jobs SET {', '.join(updates)} WHERE job_id = ?", tuple(params)
    )
    conn.commit()
    conn.close()


def log_stage(
    job_id: str, stage_name: str, status: str, logs: str = None, chunk_id: int = None, model_id: int = None
):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if stage already exists for this job (and chunk_id)
    if chunk_id is not None:
        cursor.execute(
            "SELECT id, start_time FROM job_stages WHERE job_id = ? AND stage_name = ? AND chunk_id = ?",
            (job_id, stage_name, chunk_id),
        )
    else:
        cursor.execute(
            "SELECT id, start_time FROM job_stages WHERE job_id = ? AND stage_name = ? AND chunk_id IS NULL",
            (job_id, stage_name),
        )

    row = cursor.fetchone()

    current_time = time.time()

    if row:
        end_time = current_time if status in ["completed", "failed"] else None
        
        updates = ["status = ?", "logs = ?", "end_time = ?"]
        params = [status, logs, end_time]
        if model_id is not None:
            updates.append("model_id = ?")
            params.append(model_id)
        params.append(row[0])
            
        cursor.execute(
            f"UPDATE job_stages SET {', '.join(updates)} WHERE id = ?",
            tuple(params),
        )
    else:
        end_time = current_time if status in ["completed", "failed"] else None
        cursor.execute(
            """
        INSERT INTO job_stages (job_id, stage_name, status, logs, start_time, end_time, chunk_id, model_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (job_id, stage_name, status, logs, current_time, end_time, chunk_id, model_id),
        )

    conn.commit()
    conn.close()


def get_all_jobs():
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
    SELECT j.job_id, j.status, j.created_at, v.video_name, v.video_path, j.json_path
    FROM jobs j
    JOIN videos v ON j.video_id = v.video_id
    ORDER BY j.created_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_job_stages(job_id: str):
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT stage_name, chunk_id, status, logs, start_time, end_time FROM job_stages WHERE job_id = ? ORDER BY start_time ASC",
        (job_id,),
    )
    rows = cursor.fetchall()
    conn.close()

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
            "timestamp": row["start_time"],  # backwards compatibility for UI
        }
    return stages


def get_job(job_id: str):
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        """
    SELECT j.job_id, j.status, j.created_at, v.video_name, v.video_path, j.json_path, j.metadata, j.num_chunks, j.video_id
    FROM jobs j
    JOIN videos v ON j.video_id = v.video_id
    WHERE j.job_id = ?
    """,
        (job_id,),
    )
    row = cursor.fetchone()
    conn.close()

    if row:
        job_dict = dict(row)
        try:
            job_dict["metadata"] = json.loads(job_dict.get("metadata") or "{}")
        except Exception:
            job_dict["metadata"] = {}
        return job_dict
    return None


def get_completed_stages(job_id: str):
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        'SELECT chunk_id, stage_name, logs FROM job_stages WHERE job_id = ? AND status = "completed"',
        (job_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def queue_render_task(task_id: str, job_id: str, variant_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = time.time()
    cursor.execute(
        """
    INSERT OR IGNORE INTO job_renders (id, job_id, variant_id, status, error_logs, created_at, updated_at)
    VALUES (?, ?, ?, 'queued', '', ?, ?)
    """,
        (task_id, job_id, variant_id, now, now),
    )
    conn.commit()
    conn.close()


def update_render_status(
    task_id: str, status: str, error_logs: str = "", outputs: list = None
):
    conn = get_db_connection()
    cursor = conn.cursor()
    outputs_str = json.dumps(outputs) if outputs is not None else None

    if outputs_str is not None:
        cursor.execute(
            """
        UPDATE job_renders SET status = ?, error_logs = ?, outputs = ?, updated_at = ? WHERE id = ?
        """,
            (status, error_logs, outputs_str, time.time(), task_id),
        )
    else:
        cursor.execute(
            """
        UPDATE job_renders SET status = ?, error_logs = ?, updated_at = ? WHERE id = ?
        """,
            (status, error_logs, time.time(), task_id),
        )
    conn.commit()
    conn.close()


def get_render_statuses(job_id: str):
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT variant_id, status, error_logs, outputs FROM job_renders WHERE job_id = ?",
        (job_id,),
    )
    rows = cursor.fetchall()
    conn.close()

    results = []
    for row in rows:
        d = dict(row)
        try:
            d["outputs"] = json.loads(d["outputs"]) if d["outputs"] else []
        except Exception:
            d["outputs"] = []
        results.append(d)
    return results


def get_database_dump():
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r["name"] for r in cursor.fetchall()]

    dump = {}
    for table in tables:
        if table.startswith("sqlite_"):
            continue
            
        cursor.execute(f"SELECT * FROM {table}")
        rows = [dict(r) for r in cursor.fetchall()]
        
        if table == "jobs":
            for j in rows:
                try:
                    j["metadata"] = json.loads(j.get("metadata") or "{}")
                except Exception:
                    j["metadata"] = {}
        dump[table] = rows

    conn.close()
    return dump


def clear_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM job_stages")
    cursor.execute("DELETE FROM jobs")
    cursor.execute("DELETE FROM videos")
    conn.commit()
    conn.close()

def get_or_create_model(provider: str, model_name: str) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM models WHERE model_name = ?", (model_name,))
    row = cursor.fetchone()
    if row:
        model_id = row[0]
    else:
        cursor.execute(
            "INSERT INTO models (provider, model_name) VALUES (?, ?)",
            (provider, model_name)
        )
        model_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return model_id

def log_model_usage(model_id: int, prompt_tokens: int, completion_tokens: int, cost: float):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO model_usage (model_id, prompt_tokens, completion_tokens, cost, timestamp) VALUES (?, ?, ?, ?, ?)",
        (model_id, prompt_tokens, completion_tokens, cost, time.time())
    )
    conn.commit()
    conn.close()

def log_rate_limit(model_id: int, error_message: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO rate_limits (model_id, timestamp, error_message) VALUES (?, ?, ?)",
        (model_id, time.time(), error_message)
    )
    conn.commit()
    conn.close()

def get_metrics_summary():
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            m.provider,
            m.model_name,
            SUM(u.prompt_tokens) as total_prompt_tokens,
            SUM(u.completion_tokens) as total_completion_tokens,
            SUM(u.cost) as total_cost,
            COUNT(u.id) as total_requests
        FROM models m
        LEFT JOIN model_usage u ON m.id = u.model_id
        GROUP BY m.id
    """)
    usage_data = [dict(r) for r in cursor.fetchall()]
    
    cursor.execute("""
        SELECT 
            m.model_name,
            r.timestamp,
            r.error_message
        FROM rate_limits r
        JOIN models m ON r.model_id = m.id
        ORDER BY r.timestamp DESC LIMIT 50
    """)
    rate_limits = [dict(r) for r in cursor.fetchall()]
    
    conn.close()
    return {
        "usage": usage_data,
        "rate_limits": rate_limits
    }

def seed_game_data(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM dim_game_types")
    if cursor.fetchone()[0] > 0:
        return # already seeded
        
    # Seed genres
    genres = ["fps", "moba", "br", "generic"]
    for genre in genres:
        cursor.execute("INSERT INTO dim_game_types (game_genre) VALUES (?)", (genre,))
    conn.commit()
    
    cursor.execute("SELECT id, game_genre FROM dim_game_types")
    genre_map = {row[1]: row[0] for row in cursor.fetchall()}

    keywords = {
        "fps": ["loud gunshot or heavy gunfire", "weapon reloading mechanical click", "fast footsteps running", "planting bomb or defusing beeping", "heavy explosion blast", "sword slash or knife swing", "victory cheer or fanfare", "dying groan or scream"],
        "moba": ["loud gunshot or heavy gunfire", "weapon reloading mechanical click", "fast footsteps running", "planting bomb or defusing beeping", "heavy explosion blast", "sword slash or knife swing", "victory cheer or fanfare", "dying groan or scream"],
        "br": ["loud gunshot or heavy gunfire", "weapon reloading mechanical click", "fast footsteps running", "planting bomb or defusing beeping", "heavy explosion blast", "sword slash or knife swing", "victory cheer or fanfare", "dying groan or scream"],
        "generic": ["loud gunshot or heavy gunfire", "weapon reloading mechanical click", "fast footsteps running", "planting bomb or defusing beeping", "heavy explosion blast", "sword slash or knife swing", "victory cheer or fanfare", "dying groan or scream"]
    }
    for genre, words in keywords.items():
        genre_id = genre_map[genre]
        for word in words:
            cursor.execute("INSERT INTO audio_keywords (game_type_id, keyword) VALUES (?, ?)", (genre_id, word))

    games = [
        ("Valorant", "fps"),
        ("CS:GO", "fps"),
        ("Call of Duty", "fps"),
        ("League of Legends", "moba"),
        ("Dota 2", "moba"),
        ("Apex Legends", "br"),
        ("Fortnite", "br"),
        ("PUBG", "br"),
        ("Generic Game", "generic")
    ]
    
    workspace_dir = os.path.join(os.path.dirname(__file__), "workspace")
    games_dir = os.path.join(workspace_dir, "games")
    os.makedirs(games_dir, exist_ok=True)

    for game_name, genre in games:
        genre_id = genre_map[genre]
        game_uuid = str(uuid.uuid4())
        folder_path = os.path.join("workspace", "games", game_uuid)
        abs_folder_path = os.path.join(os.path.dirname(__file__), folder_path)
        os.makedirs(abs_folder_path, exist_ok=True)
        
        context_file = os.path.join(abs_folder_path, f"context.txt")
        with open(context_file, "w") as f:
            f.write(f"Context and lore for {game_name}.\n")
            
        cursor.execute("INSERT INTO dim_games (game_type_id, game_name, folder_path) VALUES (?, ?, ?)", (genre_id, game_name, folder_path))
    
    conn.commit()

def get_supported_games():
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
        SELECT g.id, g.game_name, t.game_genre, t.id as game_type_id, g.folder_path
        FROM dim_games g
        JOIN dim_game_types t ON g.game_type_id = t.id
        ORDER BY g.game_name ASC
    ''')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_game_types():
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT id, game_genre FROM dim_game_types ORDER BY game_genre ASC')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_audio_keywords_by_game(game_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT k.keyword 
        FROM audio_keywords k
        JOIN dim_games g ON g.game_type_id = k.game_type_id
        WHERE g.id = ?
    ''', (game_id,))
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

def get_game_context_path(game_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT folder_path FROM dim_games WHERE id = ?', (game_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return os.path.join(os.path.dirname(__file__), row[0], 'context.txt')
    return None

def create_game(game_name: str, game_type_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    game_uuid = str(uuid.uuid4())
    folder_path = os.path.join("workspace", "games", game_uuid)
    abs_folder_path = os.path.join(os.path.dirname(__file__), folder_path)
    os.makedirs(abs_folder_path, exist_ok=True)
    
    context_file = os.path.join(abs_folder_path, f"context.txt")
    with open(context_file, "w") as f:
        f.write(f"Context and lore for {game_name}.\n")
        
    cursor.execute(
        "INSERT INTO dim_games (game_type_id, game_name, folder_path) VALUES (?, ?, ?)",
        (game_type_id, game_name, folder_path)
    )
    conn.commit()
    conn.close()
