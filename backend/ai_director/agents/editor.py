from ai_director.config_manager import get_config
import logging
import google.genai as genai
from google.genai import types
from pipeline.capabilities.effects.registry import get_capabilities_menu

logger = logging.getLogger(__name__)

EDITOR_PROMPT_TEMPLATE = """You are the Editor (Technical Translation).
You will receive the Director's creative vision for multiple video variants.
Your job is to translate their "Vibes" and "Magic" into concrete, technical FFMPEG directives supported by our Engine.

=== GLOBAL METADATA ===
Game: {game_name}
Region: {region}
Vibe: {vibe}

{capabilities_menu}

INSTRUCTIONS:
1. Parse the Director's Vision.
2. For every phase in every variant, assign specific effects from the menu that map to the Director's Hyper-Editing and Visual Effects.
3. Time logic: You must define the `relative_start_time` (float seconds from the start of the specific Phase, NOT the whole video) and `duration` for each effect.
4. Punch-ins: Read the Director's framing instructions (e.g., zooms, crops). Define an array of `visual_punch_in_timestamps` (float seconds RELATIVE to the start of the Phase) for when the camera should rapidly zoom in.
5. Transitions: Assign a `transition_in` string (from the XFADE transitions menu) for every phase EXCEPT the very first phase.
6. Text Overlays: Pass through the EXACT Text Overlays prescribed by the Director. If the Director said "No text needed", leave it blank. DO NOT INVENT CHEESY TITLES.
7. Spatial Focus: The Director will provide a `Focus: [start_x, end_x]`. You must output this exactly as `start_focus_x: start_x` and `end_focus_x: end_x` in your breakdown.
8. Background Audio: You must include the `BACKGROUND AUDIO:` string exactly as the Director specified it.
9. DO NOT OUTPUT JSON. Output a strict technical breakdown text.

Example Editor Breakdown:
VARIANT: The 1v3 Site Anchor
BACKGROUND AUDIO: hype_trap_beat.mp3
PHASES:
- Phase 1 (Setup): 15.0 - 20.0 (Duration: 5.0)
  Start Focus X: 960
  End Focus X: 960
  Text: ""
  Effects: [{{'effect_name': 'vhs_overlay', 'relative_start_time': 0.0, 'duration': 5.0}}]
  Punch-ins: [2.5]
- Phase 2 (Struggle): 20.0 - 25.5 (Duration: 5.5)
  Start Focus X: 960
  End Focus X: 1200
  Transition In: "pixelize"
  Text: "1 HP!"
  Effects: [{{'effect_name': 'screen_shake', 'relative_start_time': 0.0, 'duration': 5.5}}, {{'effect_name': 'desaturate', 'relative_start_time': 0.0, 'duration': 5.5}}]
  Punch-ins: [1.2, 4.0]

Now, translate this Vision into technical directives:
"""

class EditorAgent:
    def __init__(self):
        self.client = genai.Client()

    def execute(self, director_vision: str, metadata: dict) -> str:
        logger.info("Editor Agent translating magic into technical directives...")
        
        dynamic_menu = get_capabilities_menu()
        final_prompt = EDITOR_PROMPT_TEMPLATE.format(
            game_name=metadata.get("game_name", "Unknown"),
            region=metadata.get("region", "Global"),
            vibe=metadata.get("vibe", "Standard"),
            capabilities_menu=dynamic_menu
        )
        
        response = self.client.models.generate_content(
            model=get_config()["models"]["editor"],
            contents=[final_prompt + "\n\n=== DIRECTOR VISION ===\n" + director_vision],
            config=types.GenerateContentConfig(temperature=0.4)
        )
        return response.text
