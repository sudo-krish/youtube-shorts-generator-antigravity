from pydantic import BaseModel, Field
from typing import List


class VideoEffect(BaseModel):
    effect_name: str
    relative_start_time: float
    duration: float


class VideoPhase(BaseModel):
    phase_id: str = Field(
        description="A unique ID/name for this phase (e.g., 'setup', 'punchline', 'hook')"
    )
    transition_in: str = Field(
        description="The xfade transition name to use when entering this phase (e.g., 'pixelize', 'fade', 'wipeleft'). Should be null for the very first phase."
    )
    start_time: float = Field(
        description="ABSOLUTE start time in float seconds from VOD start."
    )
    end_time: float = Field(
        description="ABSOLUTE end time in float seconds from VOD start."
    )
    story_text: str = Field(description="Narrative uppercase text for this phase.")
    visual_punch_in_timestamps: List[float] = Field(
        description="Array of float seconds RELATIVE to the start of this specific phase."
    )
    start_focus_x: float = Field(
        default=960.0,
        description="The spatial X coordinate (0-1920) for the primary action at the START of this phase.",
    )
    end_focus_x: float = Field(
        default=960.0,
        description="The spatial X coordinate (0-1920) for the primary action at the END of this phase.",
    )
    effects: List[VideoEffect]


class ViralShortBlueprint(BaseModel):
    variant_id: str = Field(
        description="A unique name for this variation (e.g., 'funny_fail', 'intense_clutch')."
    )
    template_name: str = Field(description="The name of the Story Template used.")
    background_audio_track: str = Field(
        default="bgm.mp3",
        description="The filename of the semantic audio track selected to score this video.",
    )
    phases: List[VideoPhase] = Field(
        description="A dynamic array of N phases that make up this short."
    )


class FactoryTimeline(BaseModel):
    shorts: List[ViralShortBlueprint] = Field(
        description="An array of distinct, completely different viral short variants extracted from the footage."
    )
