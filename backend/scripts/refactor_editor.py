import re
from pathlib import Path

# Fix cutter.py
cutter_path = Path("modules/media/editor/cutter.py")
content = cutter_path.read_text()
content = content.replace("import os\n", "import os\nfrom core.file_manager import file_manager\nfrom pathlib import Path\n")
content = re.sub(r'out_file = os\.path\.join\(out_dir, f"\{base_name\}\.mp4"\)', 
                 r'out_file = file_manager.get_absolute_path("video_chunk", f"{base_name}.mp4")', content)
content = re.sub(r'json_file = os\.path\.join\(out_dir, f"\{base_name\}\.json"\)', 
                 r'json_file = file_manager.get_absolute_path("video_chunk", f"{base_name}.json")', content)
content = re.sub(r'with open\(json_file, "w"\) as jf:\n\s+json\.dump\(blueprint, jf, indent=2\)', 
                 r'file_manager.write_json("video_chunk", Path(json_file).name, blueprint)', content)
content = re.sub(r'os\.path\.splitext\(os\.path\.basename\(video_path\)\)\[0\]', 
                 r'Path(video_path).stem', content)
cutter_path.write_text(content)


# Fix tree_generator.py
tree_path = Path("modules/media/editor/tree_generator.py")
content = tree_path.read_text()
content = content.replace("import os\n", "import os\nfrom core.file_manager import file_manager\nfrom pathlib import Path\n")

# Json load
json_block = """        if os.path.exists(json_path):
            with open(json_path, "r") as f:
                meta = json.load(f)"""
new_json = """        try:
            meta = file_manager.read_json("video_chunk", Path(json_path).name)
        except Exception:
            pass"""
content = content.replace(json_block, new_json)

# Concat write
concat_write = """    with open(concat_txt, "w") as f:
        f.write(f"file '{os.path.abspath(hook_out)}'\\n")
        f.write(f"file '{os.path.abspath(body_output_path)}'\\n")"""
new_concat_write = """    file_manager.write_text("tmp", Path(concat_txt).name, f"file '{file_manager.get_absolute_path('video_chunk', Path(hook_out).name)}'\\nfile '{file_manager.get_absolute_path('video_chunk', Path(body_output_path).name)}'\\n")"""
content = content.replace(concat_write, new_concat_write)

# Os remove
content = re.sub(r'if os\.path\.exists\((.*?)\):\n\s+os\.remove\(\1\)', r'file_manager.delete_file("tmp", Path(\1).name)', content)

tree_path.write_text(content)
print("Done refactoring editor.")
