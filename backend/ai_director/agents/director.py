from ai_director.config_manager import get_config
import logging
from ai_director.llm_client import LLMClient
from google.genai import types

logger = logging.getLogger(__name__)

DIRECTOR_PROMPT = """You are the AI Director (Creativity & Magic) for high-retention YouTube Shorts.
You will be provided with an Observer's Context Log of a gaming video.
Your job is to read this log and define the global visual vibe, soundscape, and stylistic hyper-editing rules for this specific VOD.

CRITICAL TONE ISSUES TO AVOID:
- DO NOT use vague cinematic descriptions (e.g., "The camera feels frantic").

=== GLOBAL METADATA ===
Game: {game_name}
Game Genre: {game_type}
Player Skill Level: {player_skill}
Region: {region}

=== PRE-GENERATED LOCAL SFX LIBRARY ===
{sfx_library}

=== PRE-GENERATED LOCAL MUSIC LIBRARY ===
{music_library}

INSTRUCTIONS:
You must dictate the HYPER-EDITING, VISUAL EFFECTS, and AUDIO DESIGN rules for the Editor to use.
- Semantic Audio (BGM): You MUST select EXACTLY ONE music track filename from the Local Music Library to act as the overarching background score.
- Global SFX rules: Suggest exactly which impact/whoosh sounds from the SFX library should be used.
- Global Hyper-Editing Style: Define the visual pacing, transition style, and color grading vibe (e.g. "Aggressive 150% zoom punches on kills", "VHS retro filters on fails").

DO NOT OUTPUT JSON. Output a structured textual Vibe & Rule book.

Example Director Pitch:
BACKGROUND AUDIO: hype_trap_beat.mp3
GLOBAL STYLE: Aggressive 150% zoom punches on the crosshair. Motion blur tracking the dash.
SFX RULES: Use 'riser.mp3' for tension building, and 'impact.mp3' for heavy kills.
"""


class DirectorAgent:
    def execute(
        self,
        observer_context: str,
        metadata: dict,
        sfx_library: str,
        music_library: str,
    ) -> str:
        logger.info("Director Agent injecting magic and vibes with SFX context...")
        client = LLMClient()

        prompt = DIRECTOR_PROMPT.format(
            game_name=metadata.get("game_name", "Unknown"),
            game_type=metadata.get("game_type", "Unknown"),
            player_skill=metadata.get("player_skill", "Average"),
            region=metadata.get("region", "Global"),
            sfx_library=sfx_library,
            music_library=music_library,
        )

        return client.generate_content(
            model=get_config()["models"]["director"],
            contents=[prompt + "\n\n=== OBSERVER CONTEXT ===\n" + observer_context],
            config=types.GenerateContentConfig(temperature=0.8),
        )
