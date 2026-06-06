from pydantic import BaseModel, Field
from typing import List

class VideoEffect(BaseModel):
    effect_name: str
    relative_start_time: float
    duration: float

class CombatPhase(BaseModel):
    start_time: float = Field(description="ABSOLUTE start time in float seconds (e.g., 215.5). NEVER use MM:SS.")
    end_time: float = Field(description="ABSOLUTE end time in float seconds.")
    story_text: str = Field(description="Motivational uppercase text under 6 words.")
    visual_punch_in_timestamps: List[float] = Field(description="Array of float seconds RELATIVE to the start of this specific clip.")
    effects: List[VideoEffect]

class FightArc(BaseModel):
    fight_number: int
    proposition: CombatPhase
    struggle: CombatPhase
    result: CombatPhase

class ViralShortsExtraction(BaseModel):
    top_fights: List[FightArc] = Field(description="An array of the 3 to 5 best fights found in the video.")