import os
import glob

def replace_in_files(glob_pattern, replacements):
    for filepath in glob.glob(glob_pattern, recursive=True):
        if os.path.isfile(filepath):
            with open(filepath, 'r') as f:
                content = f.read()
            original_content = content
            for old_text, new_text in replacements.items():
                content = content.replace(old_text, new_text)
            
            if content != original_content:
                with open(filepath, 'w') as f:
                    f.write(content)
                print(f"Updated {filepath}")

replacements = {
    'core.llm_client': 'modules.ai.llm_client',
    'core.config_manager': 'modules.ai.config_manager',
    'core.orchestrator_schemas': 'modules.orchestrator.schemas'
}

replace_in_files('backend/**/*.py', replacements)
