import os
import importlib.util
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

REGISTERED_SCHEMAS = {}

def load_schemas(base_dir: str):
    """
    Auto-discovers any schema.py files under the modules directory,
    imports them, and extracts Pydantic BaseModels to register them.
    """
    for root, _, files in os.walk(base_dir):
        if "schema.py" in files:
            file_path = os.path.join(root, "schema.py")
            module_name = "modules." + os.path.relpath(file_path, base_dir).replace(os.sep, ".")[:-3]
            
            try:
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if isinstance(attr, type) and issubclass(attr, BaseModel) and attr is not BaseModel:
                        tablename = getattr(attr, "__tablename__", attr.__name__.lower())
                        REGISTERED_SCHEMAS[tablename] = attr
                        logger.info(f"Registered schema: {tablename} from {module_name}")
                        
            except Exception as e:
                logger.error(f"Failed to load schema from {file_path}: {e}")

# Base module directory is two levels up from this file's dir
MODULES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "modules")
load_schemas(MODULES_DIR)
