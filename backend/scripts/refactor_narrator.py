import re
from pathlib import Path

narrator_path = Path("modules/ai/agents/roles/narrator.py")
content = narrator_path.read_text()

content = content.replace("import os\nimport glob\n", "from core.file_manager import file_manager\nfrom pathlib import Path\n")

# Replace os.path.exists
content = content.replace("if not os.path.exists(frame_dir):", "if not Path(frame_dir).exists():")

# Replace glob
content = content.replace('frame_files = sorted(glob.glob(os.path.join(frame_dir, "frame_*.jpg")))', 
                          'frame_files = sorted([str(p) for p in Path(frame_dir).glob("frame_*.jpg")])')

# Replace basename
content = content.replace('basename = os.path.basename(frame_path)', 'basename = Path(frame_path).name')

# Replace os.remove
content = content.replace('os.remove(frame_path)', 'file_manager.delete_file("tmp", Path(frame_path).name)')

narrator_path.write_text(content)
print("Done refactoring narrator.")
