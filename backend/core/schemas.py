from pydantic import BaseModel
from typing import Dict, Any

class GenericRequest(BaseModel):
    """
    Standard input payload for a Nano-Service Lambda.
    Expected to contain file paths or state variables.
    """
    payload: Dict[str, Any]

class GenericResponse(BaseModel):
    """
    Standard output payload from a Nano-Service Lambda.
    Expected to contain the path to the newly generated JSON state file.
    """
    output: Dict[str, Any]
