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
    'modules.media.generator.generator.capabilities': 'modules.media.editor.edits',
    'modules.media.generator.capabilities': 'modules.media.editor.edits',
    'app.generator.capabilities': 'modules.media.editor.edits',
    'modules.media.generator.generator': 'modules.media.editor',
    'modules.media.generator': 'modules.media.editor',
    '/api/media/generator/generator': '/api/media/editor',
    '/api/media/generator': '/api/media/editor'
}

replace_in_files('backend/**/*.py', replacements)
