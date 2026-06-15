import os
import sqlite3
import re
import shutil

DB_PATH = "backend/runs.db"
AGENTS_DIR = "backend/outputs/agents"

def migrate_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Add columns if they don't exist
    try:
        cursor.execute("ALTER TABLE jobs ADD COLUMN num_chunks INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        print("num_chunks column already exists in jobs")

    try:
        cursor.execute("ALTER TABLE job_stages ADD COLUMN chunk_id INTEGER")
    except sqlite3.OperationalError:
        print("chunk_id column already exists in job_stages")

    # Migrate job_stages
    cursor.execute("SELECT id, stage_name FROM job_stages")
    rows = cursor.fetchall()
    
    for row_id, stage_name in rows:
        match = re.match(r"^chunk_(\d+)_(.+)$", stage_name)
        if match:
            chunk_id = int(match.group(1))
            new_stage_name = match.group(2)
            cursor.execute(
                "UPDATE job_stages SET chunk_id = ?, stage_name = ? WHERE id = ?",
                (chunk_id, new_stage_name, row_id)
            )

    # Migrate num_chunks in jobs
    cursor.execute("SELECT job_id FROM jobs")
    job_ids = [row[0] for row in cursor.fetchall()]

    for job_id in job_ids:
        cursor.execute("SELECT MAX(chunk_id) FROM job_stages WHERE job_id = ?", (job_id,))
        max_chunk = cursor.fetchone()[0]
        num_chunks = (max_chunk + 1) if max_chunk is not None else 0
        cursor.execute("UPDATE jobs SET num_chunks = ? WHERE job_id = ?", (num_chunks, job_id))

    conn.commit()
    conn.close()
    print("Database migration complete.")

def migrate_files():
    if not os.path.exists(AGENTS_DIR):
        print("No agents directory found.")
        return

    for job_id in os.listdir(AGENTS_DIR):
        job_path = os.path.join(AGENTS_DIR, job_id)
        if not os.path.isdir(job_path):
            continue

        for file_name in os.listdir(job_path):
            file_path = os.path.join(job_path, file_name)
            if not os.path.isfile(file_path):
                continue
            
            match = re.match(r"^chunk_(\d+)_(.+)\.txt$", file_name)
            if match:
                chunk_id = match.group(1)
                new_stage_name = match.group(2) + ".txt"
                
                chunk_dir = os.path.join(job_path, chunk_id)
                os.makedirs(chunk_dir, exist_ok=True)
                
                new_file_path = os.path.join(chunk_dir, new_stage_name)
                shutil.move(file_path, new_file_path)
                print(f"Moved {file_path} -> {new_file_path}")

if __name__ == "__main__":
    print("Starting migration...")
    migrate_db()
    migrate_files()
    print("Migration finished successfully.")
