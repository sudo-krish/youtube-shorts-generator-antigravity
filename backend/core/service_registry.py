import os
import importlib.util
import logging

logger = logging.getLogger(__name__)

_SERVICES = {}

def load_services(base_dir: str):
    """
    Auto-discovers any service.py files under the modules directory,
    imports them, and extracts instances ending with '_service' to register them.
    """
    for root, _, files in os.walk(base_dir):
        if "service.py" in files:
            file_path = os.path.join(root, "service.py")
            module_name = "modules." + os.path.relpath(file_path, base_dir).replace(os.sep, ".")[:-3]
            
            try:
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                for attr_name in dir(module):
                    if attr_name.endswith("_service"):
                        attr = getattr(module, attr_name)
                        # We register the service using the prefix (e.g., 'editor' from 'editor_service')
                        service_name = attr_name.replace("_service", "")
                        _SERVICES[service_name] = attr
                        logger.info(f"Registered Domain Service: {service_name} -> {attr.__class__.__name__}")
                        
            except Exception as e:
                logger.error(f"Failed to load service from {file_path}: {e}")

# Base module directory is two levels up from this file's dir
MODULES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "modules")
load_services(MODULES_DIR)

def get_service(name: str):
    """
    Retrieves a service by name.
    If the architecture shifts to lambdas in the future, this method can dynamically
    return an HTTP Proxy object instead of the local class.
    """
    service = _SERVICES.get(name)
    if not service:
        raise ValueError(f"Service '{name}' not found in the registry.")
    return service
