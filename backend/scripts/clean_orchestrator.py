import re
from pathlib import Path

orch_router_path = Path("backend/modules/orchestrator/router.py")
content = orch_router_path.read_text()

# Remove the endpoints that belong in /jobs, /renders, /factory-status
# These are: websocket_logs, cancel_job, list_jobs_endpoint, get_job_stages_endpoint, get_node_result, get_status, get_logs, render_batch, get_renders_endpoint, get_factory_status

patterns_to_remove = [
    r'@router\.websocket\("/jobs/\{job_id\}/logs/stream"\)[\s\S]*?(?=@router|$)',
    r'@router\.post\("/jobs/\{job_id\}/cancel"\)[\s\S]*?(?=@router|$)',
    r'@router\.get\("/jobs"\)[\s\S]*?(?=@router|$)',
    r'@router\.get\("/jobs/\{job_id\}/stages"\)[\s\S]*?(?=@router|$)',
    r'@router\.get\("/jobs/\{job_id\}/nodes/\{node_id\}"\)[\s\S]*?(?=@router|$)',
    r'@router\.get\("/jobs/\{job_id\}/status"\)[\s\S]*?(?=@router|$)',
    r'@router\.get\("/jobs/\{job_id\}/logs"\)[\s\S]*?(?=@router|$)',
    r'@router\.post\("/jobs/\{job_id\}/render/batch"\)[\s\S]*?(?=@router|$)',
    r'@router\.get\("/renders/\{job_id\}"\)[\s\S]*?(?=@router|$)',
    r'@router\.get\("/factory-status"\)[\s\S]*?(?=@router|$)'
]

for pattern in patterns_to_remove:
    content = re.sub(pattern, '', content)


# Now fix the raw OS operations for file manager in analyze and redrive endpoints

content = content.replace("import os", "from core.file_manager import file_manager")

run_orch_job_old = """    log_dir = os.path.join(OUTPUTS_DIR, "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, f"{job_id}.log")

    if not any(isinstance(h, logging.FileHandler) and h.baseFilename == os.path.abspath(log_path) for h in job_logger.handlers):"""
run_orch_job_new = """    log_path = file_manager.get_absolute_path("logs", f"{job_id}.log")

    if not any(isinstance(h, logging.FileHandler) and h.baseFilename == log_path for h in job_logger.handlers):"""
content = content.replace(run_orch_job_old, run_orch_job_new)


save_json_old = """        base_name = os.path.splitext(os.path.basename(video_path))[0]
        output_path = os.path.join(ASSETS_DIR, f"{base_name}_segments.json")
        with open(output_path, "w") as f:
            json.dump(output_json, f, indent=2)"""
save_json_new = """        from pathlib import Path
        base_name = Path(video_path).stem
        file_manager.write_json("base_asset", f"{base_name}_segments.json", output_json)
        output_path = file_manager.get_absolute_path("base_asset", f"{base_name}_segments.json")"""
content = content.replace(save_json_old, save_json_new)


redrive_read_old = """            stage_file = os.path.join(agents_dir, f"chunk_{chunk_id}_{stage_name}.json")
            if os.path.exists(stage_file):
                with open(stage_file, "r") as f:
                    f.seek(0)
                    resume_state[chunk_id][stage_name] = f.read()"""
redrive_read_new = """            try:
                data = file_manager.read_text("agent_output", f"{job_id}/chunk_{chunk_id}_{stage_name}.json")
                resume_state[chunk_id][stage_name] = data
            except Exception:
                pass"""
content = content.replace(redrive_read_old, redrive_read_new)

orch_router_path.write_text(content)
print("Updated orchestrator/router.py")
