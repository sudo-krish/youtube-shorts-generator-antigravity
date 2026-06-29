import re
from pathlib import Path

# Refactor manager.py
manager_path = Path("modules/orchestrator/manager.py")
content = manager_path.read_text()
content = content.replace("import os\n", "from core.file_manager import file_manager\nfrom pathlib import Path\n")
# Remove ASSETS_DIR definition
content = re.sub(r'ASSETS_DIR = os\.path\.join\([^)]+\)\n\s*os\.makedirs\(ASSETS_DIR, exist_ok=True\)', '', content)
# Replace agent output saving
save_state_old = """                agents_dir = os.path.join(
                    os.path.dirname(ASSETS_DIR),
                    "outputs",
                    "agents",
                    job_id
                )
                
                os.makedirs(agents_dir, exist_ok=True)
                with open(os.path.join(agents_dir, f"{step_name}.txt"), "w") as f:
                    f.write(str(state_update))"""

save_state_new = """                file_manager.write_text("agent_output", f"{job_id}/{step_name}.txt", str(state_update))"""
content = content.replace(save_state_old, save_state_new)
manager_path.write_text(content)


# Refactor router.py
router_path = Path("modules/orchestrator/router.py")
content = router_path.read_text()
content = content.replace("import os\n", "import asyncio\nfrom core.file_manager import file_manager\nfrom pathlib import Path\n")
# Remove ASSETS_DIR, OUTPUTS_DIR
content = re.sub(r'ASSETS_DIR = [^\n]+\nOUTPUTS_DIR = [^\n]+\n', '', content)

# _setup_job_logger
setup_log_old = """    log_dir = os.path.join(OUTPUTS_DIR, "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, f"{job_id}.log")
    
    if not any(isinstance(h, logging.FileHandler) and h.baseFilename == os.path.abspath(log_path) for h in job_logger.handlers):
        file_handler = logging.FileHandler(log_path)"""
setup_log_new = """    log_path = file_manager.get_absolute_path("logs", f"{job_id}.log")
    
    if not any(isinstance(h, logging.FileHandler) and h.baseFilename == log_path for h in job_logger.handlers):
        file_handler = logging.FileHandler(log_path)"""
content = content.replace(setup_log_old, setup_log_new)

# log stream
stream_old = """    log_path = os.path.join(OUTPUTS_DIR, "logs", f"{job_id}.log")
    
    async def log_generator():
        while not os.path.exists(log_path):
            await asyncio.sleep(0.5)
            
        with open(log_path, "r") as f:"""
stream_new = """    log_path = file_manager.get_absolute_path("logs", f"{job_id}.log")
    
    async def log_generator():
        while not Path(log_path).exists():
            await asyncio.sleep(0.5)
            
        with open(log_path, "r") as f:"""
content = content.replace(stream_old, stream_new)

# agents pipeline logs
agents_old = """    agents_dir = os.path.join(OUTPUTS_DIR, "agents", job_id)
    os.makedirs(agents_dir, exist_ok=True)"""
content = content.replace(agents_old, "")

read_agents_old = """            stage_file = os.path.join(agents_dir, f"chunk_{chunk_id}_{stage_name}.json")
            if os.path.exists(stage_file):
                with open(stage_file, "r") as f:
                    chunk_data[f"{stage_name}_payload"] = json.load(f)"""
read_agents_new = """            try:
                chunk_data[f"{stage_name}_payload"] = file_manager.read_json("agent_output", f"{job_id}/chunk_{chunk_id}_{stage_name}.json")
            except Exception:
                pass"""
content = content.replace(read_agents_old, read_agents_new)

# /logs direct
logs_old = """    log_path = os.path.join(OUTPUTS_DIR, "logs", f"{job_id}.log")
    if not os.path.exists(log_path):
        return {"logs": []}
    with open(log_path, "r") as f:"""
logs_new = """    try:
        content = file_manager.read_text("logs", f"{job_id}.log")
        return {"logs": content.splitlines()}
    except Exception:
        return {"logs": []}
"""
content = re.sub(r'    log_path = os\.path\.join\(OUTPUTS_DIR, "logs", f"\{job_id\}\.log"\)\n    if not os\.path\.exists\(log_path\):\n        return \{"logs": \[\]\}\n    with open\(log_path, "r"\) as f:\n        return \{"logs": f\.read\(\)\.splitlines\(\)\}', logs_new, content)

# get_ai_tree
ai_tree_old = """    agents_dir = os.path.join(OUTPUTS_DIR, "agents", job_id)
    for filename in os.listdir(agents_dir):
        if filename.endswith(".json") and filename.startswith("chunk_"):
            with open(os.path.join(agents_dir, filename), "r") as f:
                data = json.load(f)"""
ai_tree_new = """    files = file_manager.list_files("agent_output", f"{job_id}/chunk_*.json")
    for file_path in files:
        data = file_manager.read_json("agent_output", f"{job_id}/{Path(file_path).name}")
"""
content = content.replace(ai_tree_old, ai_tree_new)

# Write output file
write_segments_old = """        base_name = os.path.splitext(os.path.basename(video_path))[0]
        output_path = os.path.join(ASSETS_DIR, f"{base_name}_segments.json")
        with open(output_path, "w") as f:
            json.dump(pipeline_output, f, indent=2)"""
write_segments_new = """        base_name = Path(video_path).stem
        file_manager.write_json("base_asset", f"{base_name}_segments.json", pipeline_output)"""
content = content.replace(write_segments_old, write_segments_new)

router_path.write_text(content)
print("Done refactoring orchestrator.")
