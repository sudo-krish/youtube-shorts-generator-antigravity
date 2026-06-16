from app.orchestrator.config_manager import get_config
import logging
from app.orchestrator.llm_client import LLMClient
from google.genai import types
from app.generator.capabilities.effects.registry import get_capabilities_menu

logger = logging.getLogger(__name__)

EDITOR_PROMPT_TEMPLATE = """You are the Editor (Technical Translation).
You will receive the Scriptwriter's Narrative Scripts and the Director's creative Vibe rules.
Your job is to translate these Scripts and Vibers into concrete, technical FFMPEG directives supported by our Engine.

=== GLOBAL METADATA ===
Game: {game_name}
Region: {region}
Vibe: {vibe}

{capabilities_menu}

INSTRUCTIONS:
1. Parse the Narrative Scripts to identify the Phases.
2. Apply the Director's Vibe Rules to assign specific effects from the menu.
3. Time logic: You must define the `relative_start_time` (float seconds from the start of the specific Phase, NOT the whole video) and `duration` for each effect.
4. Punch-ins: Apply the Director's framing instructions. Define an array of `visual_punch_in_timestamps` (float seconds RELATIVE to the start of the Phase).
5. Transitions: Assign a `transition_in` string (from the XFADE transitions menu) for every phase EXCEPT the very first phase.
6. Text Overlays: Pass through the EXACT Text Overlays prescribed by the Scriptwriter. If no text needed, leave it blank. DO NOT INVENT CHEESY TITLES.
7. Spatial Focus (Dynamic Panning): The Scriptwriter may provide a `[start_x, end_x]` focus, but you must IGNORE IT and rely on the YOLO Tracking Matrix provided below. For each phase, extract the relevant YOLO tracking coordinates for the player's Head or Body over that timeframe. Output them as an array of relative keyframes: `Focus Keyframes: [{{'t': 0.0, 'x': 960}}, {{'t': 1.0, 'x': 1020}}, ...]`. `t` must be relative to the start of the Phase. If no YOLO data exists for that timeframe, fallback to a static center `[{{'t': 0.0, 'x': 960}}]`.
8. Background Audio: You must include the `BACKGROUND AUDIO:` string exactly as the Director specified it.
9. DO NOT OUTPUT JSON. Output a strict technical breakdown text.

Example Editor Breakdown:
VARIANT: The 1v3 Site Anchor
BACKGROUND AUDIO: hype_trap_beat.mp3
PHASES:
- Phase 1 (Setup): 15.0 - 20.0 (Duration: 5.0)
  Focus Keyframes: [{'t': 0.0, 'x': 960}, {'t': 1.0, 'x': 960}, {'t': 2.0, 'x': 980}]
  Text: ""
  Effects: [{'effect_name': 'vhs_overlay', 'relative_start_time': 0.0, 'duration': 5.0}]
  Punch-ins: [2.5]
- Phase 2 (Struggle): 20.0 - 25.5 (Duration: 5.5)
  Focus Keyframes: [{'t': 0.0, 'x': 980}, {'t': 1.0, 'x': 1020}, {'t': 2.0, 'x': 1100}]
  Transition In: "pixelize"
  Text: "1 HP!"
  Effects: [{'effect_name': 'screen_shake', 'relative_start_time': 0.0, 'duration': 5.5}, {'effect_name': 'desaturate', 'relative_start_time': 0.0, 'duration': 5.5}]
  Punch-ins: [1.2, 4.0]

Now, translate this Vision into technical directives:
"""


class EditorAgent:
    def execute(
        self, scripts_context: str, director_vision: str, metadata: dict, yolo_tracking: list = None
    ) -> str:
        logger.info("Editor Agent translating magic into technical directives...")
        client = LLMClient()

        dynamic_menu = get_capabilities_menu()
        final_prompt = EDITOR_PROMPT_TEMPLATE.format(
            game_name=metadata.get("game_name", "Unknown"),
            region=metadata.get("region", "Global"),
            vibe=metadata.get("vibe", "Standard"),
            capabilities_menu=dynamic_menu,
        )

        return client.generate_content(
            model=get_config()["models"]["editor"],
            contents=[
                final_prompt
                + "\n\n=== NARRATIVE SCRIPTS ===\n"
                + scripts_context
                + "\n\n=== DIRECTOR VISION ===\n"
                + director_vision
                + "\n\n=== YOLO TRACKING MATRIX ===\n"
                + str(yolo_tracking)
            ],
            config=types.GenerateContentConfig(temperature=0.4),
        )
