from pydantic import BaseModel, Field
from typing import List

class VideoEffect(BaseModel):
    effect_name: str
    relative_start_time: float
    duration: float

class VideoPhase(BaseModel):
    phase_id: str = Field(description="A unique ID/name for this phase (e.g., 'setup', 'punchline', 'hook')")
    transition_in: str = Field(description="The xfade transition name to use when entering this phase (e.g., 'pixelize', 'fade', 'wipeleft'). Should be null for the very first phase.")
    start_time: float = Field(description="ABSOLUTE start time in float seconds from VOD start.")
    end_time: float = Field(description="ABSOLUTE end time in float seconds from VOD start.")
    story_text: str = Field(description="Narrative uppercase text for this phase.")
    visual_punch_in_timestamps: List[float] = Field(description="Array of float seconds RELATIVE to the start of this specific phase.")
    effects: List[VideoEffect]

class ViralShortBlueprint(BaseModel):
    variant_id: str = Field(description="A unique name for this variation (e.g., 'funny_fail', 'intense_clutch').")
    template_name: str = Field(description="The name of the Story Template used.")
    phases: List[VideoPhase] = Field(description="A dynamic array of N phases that make up this short.")

class FactoryTimeline(BaseModel):
    shorts: List[ViralShortBlueprint] = Field(description="An array of distinct, completely different viral short variants extracted from the footage.")