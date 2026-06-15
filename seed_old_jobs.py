import os
import json
import sqlite3
import time

DB_PATH = "backend/runs.db"
AGENTS_DIR = "backend/outputs/agents"
VIDEO_ID = "ae51eb2b-92cd-441c-848c-8fb4d0fbcf18"

METADATA = {
    "game_name": "Valorant",
    "game_type": "fps",
    "region": "Asia"
}

def seed():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check existing jobs
    cursor.execute('SELECT job_id FROM jobs')
    existing_jobs = set(row[0] for row in cursor.fetchall())
    
    for job_id in os.listdir(AGENTS_DIR):
        job_dir = os.path.join(AGENTS_DIR, job_id)
        if not os.path.isdir(job_dir):
            continue
            
        if job_id not in existing_jobs:
            print(f"Seeding missing job: {job_id}")
            
            # Insert into jobs table
            cursor.execute('''
            INSERT INTO jobs (job_id, video_id, status, metadata, created_at, json_path)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (job_id, VIDEO_ID, "failed", json.dumps(METADATA), time.time(), None))
            
            # Read files and insert into job_stages
            for filename in os.listdir(job_dir):
                if filename.endswith(".txt"):
                    stage_name = filename[:-4]
                    print(f"  -> Seeding stage: {stage_name}")
                    
                    cursor.execute('''
                    INSERT INTO job_stages (job_id, stage_name, status, logs, start_time, end_time)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ''', (job_id, stage_name, "completed", "", time.time() - 100, time.time() - 50))
        else:
            # Job exists, but maybe we need to update its metadata to exactly what the user asked
            # Only if it currently has no metadata
            cursor.execute('SELECT metadata FROM jobs WHERE job_id = ?', (job_id,))
            row = cursor.fetchone()
            if row and (row[0] is None or row[0] == "{}" or row[0] == "null"):
                print(f"Updating metadata for existing job: {job_id}")
                cursor.execute('UPDATE jobs SET metadata = ? WHERE job_id = ?', (json.dumps(METADATA), job_id))

            # What if stages are missing from job_stages for this job? 
            # The user ran it recently and it failed at director.
            # But earlier chunks might have succeeded.
            pass
            
    conn.commit()
    conn.close()
    print("Done seeding DB!")

if __name__ == "__main__":
    seed()
