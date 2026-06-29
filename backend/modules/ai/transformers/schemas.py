from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class TransformerRequest(BaseModel):
    video_path: str
    duration: float
    step: float = 3.0
    game_id: Optional[str] = "valorant"

class TransformerResponse(BaseModel):
    matrix: List[Dict[str, Any]]
