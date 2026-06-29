import os
import glob

def replace_in_files(glob_pattern):
    for filepath in glob.glob(glob_pattern, recursive=True):
        if os.path.isfile(filepath):
            with open(filepath, 'r') as f:
                content = f.read()
            original_content = content
            
            content = content.replace('Field(primary_key=True)', 'Field(json_schema_extra={"primary_key": True})')
            content = content.replace('Field(index=True)', 'Field(json_schema_extra={"index": True})')
            content = content.replace('Field(unique=True)', 'Field(json_schema_extra={"unique": True})')
            content = content.replace('Field(default=None, primary_key=True, autoincrement=True)', 'Field(default=None, json_schema_extra={"primary_key": True, "autoincrement": True})')

            if content != original_content:
                with open(filepath, 'w') as f:
                    f.write(content)
                print(f"Updated {filepath}")

replace_in_files('backend/modules/**/schema.py')
