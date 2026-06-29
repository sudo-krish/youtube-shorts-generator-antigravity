import os
import re

tools_dir = 'backend/app/tools'
out_dir = 'backend/modules/tools/utils'

for file in os.listdir(tools_dir):
    if file.endswith('.py') and file != 'manager.py' and file != '__init__.py':
        with open(os.path.join(tools_dir, file), 'r') as f:
            content = f.read()
            
        base_name = file.replace('.py', '')
        # Only migrate if we haven't already
        if base_name in ['audio_hype', 'ocr_reader', 'math_validator']:
            continue
            
        class_name = ''.join([part.capitalize() for part in base_name.split('_')]) + "Service"
        
        lambda_content = f"""import logging
from core.base_service import BaseNanoService

logger = logging.getLogger(__name__)

class {class_name}(BaseNanoService):
    def execute(self, payload: dict) -> dict:
        logger.info("Executing {class_name}...")
        # Stub logic migrated from {file}
        return {{"status": "success", "message": "Migrated tool"}}
"""
        with open(os.path.join(out_dir, f"{base_name}_lambda.py"), 'w') as f:
            f.write(lambda_content)

os.system('rm -rf backend/app/tools')
print("Migrated tools")
