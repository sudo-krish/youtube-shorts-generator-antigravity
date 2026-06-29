import os
import glob

def replace_in_files(glob_pattern, old_text, new_text):
    for filepath in glob.glob(glob_pattern, recursive=True):
        if os.path.isfile(filepath):
            with open(filepath, 'r') as f:
                content = f.read()
            if old_text in content:
                content = content.replace(old_text, new_text)
                with open(filepath, 'w') as f:
                    f.write(content)
                print(f"Updated {filepath}")

replace_in_files('backend/modules/ai/transformers/**/*.py', 'app.transformers.', 'modules.ai.transformers.')
replace_in_files('backend/modules/media/generator/**/*.py', 'app.generator.', 'modules.media.generator.')

# Also the state machine calls httpx endpoints, those need updating.
replace_in_files('backend/modules/ai/transformers/matrix_builder.py', '/api/transformers/', '/api/ai/transformers/')
