import os

files_to_migrate = [
    {
        "src": "README.md",
        "dest": "docs/General/README.md",
        "domain": "General",
        "folder_path": "docs/General",
        "description": "General project overview and setup instructions.",
        "veracity_score": 4,
        "tags": ["overview", "setup", "quickstart"]
    },
    {
        "src": "backend/README.md",
        "dest": "docs/Backend/README.md",
        "domain": "Backend",
        "folder_path": "docs/Backend",
        "description": "Backend services, APIs, and audio/video processing details.",
        "veracity_score": 4,
        "tags": ["backend", "api", "python"]
    },
    {
        "src": "backend/TODO.md",
        "dest": "docs/Backend/TODO.md",
        "domain": "Backend",
        "folder_path": "docs/Backend",
        "description": "Pending tasks and roadmap for the backend.",
        "veracity_score": 3,
        "tags": ["todo", "roadmap", "backend"]
    },
    {
        "src": "backend/YOUTUBE_ALGORITHM_RULES.md",
        "dest": "docs/Architecture/YOUTUBE_ALGORITHM_RULES.md",
        "domain": "Architecture",
        "folder_path": "docs/Architecture",
        "description": "YouTube Shorts algorithm timing zones, rules, and logic for AI video slicing.",
        "veracity_score": 5,
        "tags": ["algorithm", "architecture", "rules"]
    },
    {
        "src": "frontend/README.md",
        "dest": "docs/Frontend/README.md",
        "domain": "Frontend",
        "folder_path": "docs/Frontend",
        "description": "Frontend setup, components, UI guidelines, and React details.",
        "veracity_score": 4,
        "tags": ["frontend", "ui", "react"]
    }
]

for file_info in files_to_migrate:
    src = file_info["src"]
    dest = file_info["dest"]
    if not os.path.exists(src):
        print(f"Skipping {src}, not found.")
        continue
    
    with open(src, "r", encoding="utf-8") as f:
        content = f.read()
    
    front_matter = f"""---
domain: {file_info["domain"]}
folder_path: {file_info["folder_path"]}
description: {file_info["description"]}
veracity_score: {file_info["veracity_score"]}
tags: [{', '.join(file_info['tags'])}]
---

"""
    
    with open(dest, "w", encoding="utf-8") as f:
        f.write(front_matter + content)
        
    os.remove(src)
    print(f"Migrated {src} to {dest}")
