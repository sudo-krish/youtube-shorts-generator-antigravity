import argparse
import json
import math
import os
import re
import yaml
from collections import Counter

# Path setup
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS_DIR = os.path.join(BASE_DIR, "docs")
MAP_FILE = os.path.join(DOCS_DIR, "directory_map.yaml")

def load_directory_map():
    with open(MAP_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def get_words(text):
    return re.findall(r'\w+', text.lower())

def cosine_similarity(vec1, vec2):
    intersection = set(vec1.keys()) & set(vec2.keys())
    numerator = sum([vec1[x] * vec2[x] for x in intersection])
    
    sum1 = sum([vec1[x] ** 2 for x in list(vec1.keys())])
    sum2 = sum([vec2[x] ** 2 for x in list(vec2.keys())])
    denominator = math.sqrt(sum1) * math.sqrt(sum2)
    
    if not denominator:
        return 0.0
    else:
        return float(numerator) / denominator

def find_best_folder(query, dir_map):
    query_vec = Counter(get_words(query))
    best_score = -1
    best_folder = None
    best_persona = None
    
    # Handle new memory_bank schema
    if isinstance(dir_map, dict) and "memory_bank" in dir_map:
        bank = dir_map["memory_bank"]
        for entry in bank:
            folder = entry.get("folder")
            desc_vec = Counter(get_words(entry.get("description", "")))
            score = cosine_similarity(query_vec, desc_vec)
            if score > best_score:
                best_score = score
                best_folder = folder
                best_persona = entry.get("ai_persona_modifier")
                
        # Default to General if no good match (score == 0)
        if best_score == 0:
            for entry in bank:
                if entry.get("folder") == "General":
                    return "General", entry.get("ai_persona_modifier")
            return None, None
            
        return best_folder, best_persona

    # Fallback to old schema
    for folder, info in dir_map.items():
        desc_vec = Counter(get_words(info.get("description", "")))
        score = cosine_similarity(query_vec, desc_vec)
        if score > best_score:
            best_score = score
            best_folder = folder
            best_persona = info.get("ai_persona_modifier")
            
    # Default to General if no good match (score == 0)
    if best_score == 0 and "General" in dir_map:
        return "General", dir_map["General"].get("ai_persona_modifier")
        
    return best_folder, best_persona

def parse_front_matter(content):
    if not content.startswith("---"):
        return None, content
    
    parts = content.split("---", 2)
    if len(parts) >= 3:
        try:
            return yaml.safe_load(parts[1]), parts[2]
        except yaml.YAMLError:
            return None, content
    return None, content

def find_best_file(folder, query):
    folder_path = os.path.join(DOCS_DIR, folder)
    if not os.path.exists(folder_path):
        return None, None
        
    query_vec = Counter(get_words(query))
    best_score = -1
    best_file_path = None
    best_metadata = None
    
    for filename in os.listdir(folder_path):
        if not filename.endswith(".md"):
            continue
            
        file_path = os.path.join(folder_path, filename)
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        metadata, text = parse_front_matter(content)
        
        # Combine metadata description and file content for scoring
        search_text = text
        if metadata and "description" in metadata:
            search_text += " " + metadata["description"]
        if metadata and "tags" in metadata:
            search_text += " " + " ".join(metadata["tags"])
            
        doc_vec = Counter(get_words(search_text))
        score = cosine_similarity(query_vec, doc_vec)
        
        if score > best_score:
            best_score = score
            best_file_path = file_path
            best_metadata = metadata
            
    return best_file_path, best_metadata

def main():
    parser = argparse.ArgumentParser(description="AI Memory Router")
    parser.add_argument("query", type=str, help="The search query")
    args = parser.parse_args()
    
    dir_map = load_directory_map()
    best_folder, persona = find_best_folder(args.query, dir_map)
    
    if not best_folder:
        print(json.dumps({"error": "No folders found in map."}))
        return
        
    best_file_path, best_metadata = find_best_file(best_folder, args.query)
    
    result = {
        "best_folder": best_folder,
        "ai_persona_modifier": persona,
        "best_file_path": best_file_path,
        "metadata": best_metadata
    }
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
