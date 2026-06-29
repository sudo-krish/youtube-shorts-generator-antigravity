from typing import Dict, Any

class BaseNanoService:
    """
    The root template for all Nano-Services in the system.
    Every lambda-style function must inherit from this class.
    
    If 'route' is None, the Global Registry will infer the route from 
    the file path relative to the 'modules' directory.
    """
    route: str = None
    
    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the nano-service logic.
        Must be implemented by the subclass.
        """
        raise NotImplementedError("Nano-Services must implement the execute() method.")
