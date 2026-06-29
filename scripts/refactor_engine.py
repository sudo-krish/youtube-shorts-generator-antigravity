import re
from pathlib import Path

engine_path = Path("backend/modules/media/editor/engine.py")
content = engine_path.read_text()

# Add file_manager import
content = content.replace("import shutil\nimport uuid\n", "import shutil\nimport uuid\nfrom core.file_manager import file_manager\nfrom pathlib import Path as PathLib\n")

# Replace os.remove with file_manager.delete_file
content = re.sub(r'os\.remove\((.*?)\)', r'file_manager.delete_file("tmp", PathLib(\1).name)', content)

# Special cases where they might not be 'tmp' asset types? 
# The clips are video_chunks.
content = content.replace('file_manager.delete_file("tmp", PathLib(chunk).name)', 'file_manager.delete_file("video_chunk", PathLib(chunk).name)')
content = content.replace('file_manager.delete_file("tmp", PathLib(raw_game_audio_wav).name)', 'file_manager.delete_file("tmp", PathLib(raw_game_audio_wav).name)')

# Replace os.path.exists with file_manager abstraction or just PathLib
content = re.sub(r'os\.path\.exists\((.*?)\)', r'PathLib(\1).exists()', content)

# Replace json reading
json_read_block = """        if PathLib(json_path).exists():
            with open(json_path, "r") as f:
                meta = json.load(f)"""
new_json_block = """        try:
            meta = file_manager.read_json("video_chunk", PathLib(json_path).name)
        except Exception:
            pass"""
content = content.replace(json_read_block, new_json_block)

engine_path.write_text(content)
print("engine.py refactored.")
