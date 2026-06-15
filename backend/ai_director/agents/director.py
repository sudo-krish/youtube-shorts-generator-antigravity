from ai_director.config_manager import get_config
import logging
import google.genai as genai
from google.genai import types

logger = logging.getLogger(__name__)

DIRECTOR_PROMPT = """You are the AI Director (Creativity & Magic) for high-retention YouTube Shorts.
You will be provided with a set of Narrative Scripts for a gaming video.
Your job is to read these scripts and translate them into CONCRETE, aggressive editing directives.

CRITICAL TONE ISSUES TO AVOID:
- DO NOT invent cheesy 2-5 word uppercase movie titles (e.g., "PLAN UNFOLDS", "THE CHASE").
- DO NOT use vague cinematic descriptions (e.g., "The camera feels frantic").

=== GLOBAL METADATA ===
Game: {game_name}
Game Genre: {game_type}
Player Skill Level: {player_skill}
Region: {region}

=== PRE-GENERATED LOCAL SFX LIBRARY ===
{sfx_library}

INSTRUCTIONS:
For each Phase in each Variant, you must dictate the HYPER-EDITING, VISUAL EFFECTS, and AUDIO DESIGN.
- Text Overlays: The Text Overlay MUST be the exact "Caption" provided by the Scriptwriter (the relatable, first-person story). Do not write generic hype titles.
- SFX: You MUST ONLY pick exact filenames from the Local SFX Library provided above. DO NOT hallucinate files like 'heartbeat.mp3' or 'vine_boom.mp3' if they are not in the list.
- Hyper-Editing: Specify exact framing and motion for a 9:16 vertical short. (e.g., "150% Zoom punch on the crosshair", "Motion blur tracking the dash", "Freeze frame and desaturate right before the death").

DO NOT OUTPUT JSON. Output a structured textual direction.

Example Director Pitch:
VARIANT: The 1v3 Site Anchor
PHASES:
- Phase 1 (Setup): 15.0 - 20.0
  Text: "My whole team died and left me alone on B site 😭"
  Hyper-Editing: 9:16 static crop on the player's crosshair holding the angle. Zero camera movement to emphasize the silence.
  SFX: riser.mp3 (low volume, building tension)
...
"""

class DirectorAgent:
    def __init__(self):
        self.client = genai.Client()

    def execute(self, scripts_context: str, metadata: dict, sfx_library: str) -> str:
        logger.info("Director Agent injecting magic and vibes with SFX context...")
        
        prompt = DIRECTOR_PROMPT.format(
            game_name=metadata.get("game_name", "Unknown"),
            game_type=metadata.get("game_type", "Unknown"),
            player_skill=metadata.get("player_skill", "Average"),
            region=metadata.get("region", "Global"),
            sfx_library=sfx_library
        )
        
        response = self.client.models.generate_content(
            model=get_config()["models"]["director"],
            contents=[prompt + "\n\n=== NARRATIVE SCRIPTS ===\n" + scripts_context],
            config=types.GenerateContentConfig(temperature=0.8)
        )
        return response.text
