import os

def refactor_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    # Replacements for main.py imports
    content = content.replace("from database import (", "")
    content = content.replace("    init_db,", "")
    content = content.replace("    create_job,", "")
    content = content.replace("    update_job_status,", "")
    content = content.replace("    get_all_jobs,", "")
    content = content.replace("    get_job_stages,", "")
    content = content.replace("    get_job,", "")
    content = content.replace("    create_video,", "")
    content = content.replace("    get_video,", "")
    content = content.replace("    get_completed_stages,", "")
    content = content.replace("    get_database_dump,", "")
    content = content.replace("    clear_database,", "")
    content = content.replace("    update_render_status,", "")
    content = content.replace(")", "")
    
    # Other imports
    content = content.replace("from database import get_supported_games, get_game_types", "")
    content = content.replace("from database import create_game", "")
    content = content.replace("from database import get_game_context_path", "")
    content = content.replace("from database import get_metrics_summary", "")
    content = content.replace("from database import queue_render_task", "")
    content = content.replace("from database import get_render_statuses", "")
    content = content.replace("from database import DB_PATH, get_db_connection", "")
    
    # Add top level import
    if "from core.db.manager import db" not in content:
        content = content.replace("from app.generator.engine import execute_pipeline", "from app.generator.engine import execute_pipeline\\nfrom core.db.manager import db\\nfrom core.db.connection import init_db")

    # Replace specific function calls
    content = content.replace("create_job(", "db.jobs.create(")
    content = content.replace("update_job_status(", "db.jobs.update_status(")
    content = content.replace("get_all_jobs(", "db.jobs.get_all(")
    content = content.replace("get_job_stages(", "db.jobs.get_stages(")
    content = content.replace("get_job(", "db.jobs.get(")
    content = content.replace("create_video(", "db.videos.create(")
    content = content.replace("get_video(", "db.videos.get(")
    content = content.replace("get_completed_stages(", "db.jobs.get_completed_stages(")
    content = content.replace("get_database_dump(", "db.get_database_dump(")
    content = content.replace("clear_database(", "db.clear_all(")
    content = content.replace("update_render_status(", "db.jobs.update_render(")
    content = content.replace("queue_render_task(", "db.jobs.queue_render(")
    content = content.replace("get_render_statuses(", "db.jobs.get_renders(")
    content = content.replace("get_supported_games(", "db.games.get_supported_games(")
    content = content.replace("get_game_types(", "db.games.get_game_types(")
    content = content.replace("create_game(", "db.games.create_game(")
    content = content.replace("get_game_context_path(", "db.games.get_game_context_path(")
    content = content.replace("get_metrics_summary(", "db.models.get_metrics_summary(")
    
    # Fix the raw queries inside main.py
    raw_query = '''    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE job_stages SET status = 'failed', end_time = ? WHERE job_id = ? AND status IN ('running', 'processing')",
        (time.time(), job_id),
    )
    conn.commit()
    conn.close()'''
    content = content.replace(raw_query, "    db.jobs.fail_running_stages(job_id)")
    
    # Fix the other raw query
    raw_query_2 = '''        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE job_stages SET status = 'failed', end_time = ? WHERE job_id = ? AND status IN ('running', 'processing')",
            (time.time(), job_id),
        )
        conn.commit()
        conn.close()'''
    content = content.replace(raw_query_2, "        db.jobs.fail_running_stages(job_id)")

    with open(filepath, 'w') as f:
        f.write(content)

refactor_file("backend/main.py")
