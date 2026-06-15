import sqlite3
import os
import time
import json
import logging

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), "runs.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create videos table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS videos (
        video_id TEXT PRIMARY KEY,
        video_name TEXT,
        video_path TEXT,
        created_at REAL
    )
    ''')

    # Create jobs table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS jobs (
        job_id TEXT PRIMARY KEY,
        video_id TEXT,
        status TEXT,
        created_at REAL,
        json_path TEXT,
        FOREIGN KEY (video_id) REFERENCES videos (video_id)
    )
    ''')
    
    # Create job_stages table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS job_stages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id TEXT,
        stage_name TEXT,
        status TEXT,
        logs TEXT,
        start_time REAL,
        end_time REAL,
        FOREIGN KEY (job_id) REFERENCES jobs (job_id)
    )
    ''')
    
    try:
        cursor.execute('ALTER TABLE jobs ADD COLUMN metadata TEXT')
    except sqlite3.OperationalError:
        pass # Column might already exist
    
    conn.commit()
    conn.close()
    logger.info(f"Initialized database at {DB_PATH}")

def create_video(video_id: str, video_name: str, video_path: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO videos (video_id, video_name, video_path, created_at)
    VALUES (?, ?, ?, ?)
    ''', (video_id, video_name, video_path, time.time()))
    conn.commit()
    conn.close()

def get_video(video_id: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM videos WHERE video_id = ?', (video_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def create_job(job_id: str, video_id: str, metadata: dict = None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO jobs (job_id, video_id, status, metadata, created_at, json_path)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', (job_id, video_id, "processing", json.dumps(metadata or {}), time.time(), None))
    conn.commit()
    conn.close()

def update_job_status(job_id: str, status: str, json_path: str = None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if json_path:
        cursor.execute('UPDATE jobs SET status = ?, json_path = ? WHERE job_id = ?', (status, json_path, job_id))
    else:
        cursor.execute('UPDATE jobs SET status = ? WHERE job_id = ?', (status, job_id))
    conn.commit()
    conn.close()

def log_stage(job_id: str, stage_name: str, status: str, logs: str = None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, start_time FROM job_stages WHERE job_id = ? AND stage_name = ?', (job_id, stage_name))
    row = cursor.fetchone()
    
    current_time = time.time()
    
    if row:
        end_time = current_time if status in ["completed", "failed"] else None
        cursor.execute('''
        UPDATE job_stages SET status = ?, logs = ?, end_time = ? WHERE id = ?
        ''', (status, logs, end_time, row[0]))
    else:
        end_time = current_time if status in ["completed", "failed"] else None
        cursor.execute('''
        INSERT INTO job_stages (job_id, stage_name, status, logs, start_time, end_time)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (job_id, stage_name, status, logs, current_time, end_time))
        
    conn.commit()
    conn.close()

def get_all_jobs():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
    SELECT j.job_id, j.status, j.created_at, v.video_name, v.video_path, j.json_path
    FROM jobs j
    JOIN videos v ON j.video_id = v.video_id
    ORDER BY j.created_at DESC
    ''')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_job_stages(job_id: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT stage_name, status, logs, start_time, end_time FROM job_stages WHERE job_id = ? ORDER BY start_time ASC', (job_id,))
    rows = cursor.fetchall()
    conn.close()
    
    stages = {}
    for row in rows:
        stages[row["stage_name"]] = {
            "status": row["status"],
            "logs": row["logs"],
            "start_time": row["start_time"],
            "end_time": row["end_time"],
            "timestamp": row["start_time"] # backwards compatibility for UI
        }
    return stages

def get_job(job_id: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
    SELECT j.job_id, j.status, j.created_at, v.video_name, v.video_path, j.json_path
    FROM jobs j
    JOIN videos v ON j.video_id = v.video_id
    WHERE j.job_id = ?
    ''', (job_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None
