import os

OUTPUTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outputs")

def prepare_project_directory(video_id: str) -> str:
    """Creates a dedicated directory for a specific video's generated assets."""
    proj_dir = os.path.join(OUTPUTS_DIR, video_id)
    os.makedirs(proj_dir, exist_ok=True)
    return proj_dir

def get_output_path(video_id: str, variant_id: str) -> str:
    """Gets the final rendered viral short path."""
    return os.path.join(OUTPUTS_DIR, f"{video_id}_{variant_id}_viral_short.mp4")
