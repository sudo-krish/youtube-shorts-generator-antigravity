from ..agents import BaseDynamicAgent

PROMPT = """You are the Editor (Technical Translation).
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
7. Spatial Focus (Static Center Panning): The source video is an FPS game, meaning the crosshair is ALWAYS in the exact center of the screen. You must ALWAYS output a single static keyframe locking the focus to exactly 960 (the center of a 1080p frame): `Focus Keyframes: [{'t': 0.0, 'x': 960}]`. DO NOT dynamically pan.
8. Background Audio: You must include the `BACKGROUND AUDIO:` string exactly as the Director specified it.
9. DO NOT OUTPUT JSON. Output a strict technical breakdown text.

Example Editor Breakdown:
VARIANT: The 1v3 Site Anchor
BACKGROUND AUDIO: hype_trap_beat.mp3
PHASES:
- Phase 1 (Setup): 15.0 - 20.0 (Duration: 5.0)
  Focus Keyframes: [{'t': 0.0, 'x': 960}]
  Text: ""
  Effects: [{'effect_name': 'vhs_overlay', 'relative_start_time': 0.0, 'duration': 5.0}]
  Punch-ins: [2.5]
- Phase 2 (Struggle): 20.0 - 25.5 (Duration: 5.5)
  Focus Keyframes: [{'t': 0.0, 'x': 960}]
  Transition In: "pixelize"
  Text: "1 HP!"
  Effects: [{'effect_name': 'screen_shake', 'relative_start_time': 0.0, 'duration': 5.5}, {'effect_name': 'desaturate', 'relative_start_time': 0.0, 'duration': 5.5}]
  Punch-ins: [1.2, 4.0]

Now, translate this Vision into technical directives:
"""

class EditorAgent(BaseDynamicAgent):
    name = "editor"
    prompt_template = PROMPT
    
    def execute(self, payload: dict) -> dict:
        self.logger.info("Editor Agent starting...")
        
        # Extract variables
        game_name = payload.get("game_name", "Unknown")
        region = payload.get("region", "Global")
        vibe = payload.get("vibe", "Standard")
        scripts_context = payload.get("scripts_context", "None")
        director_vision = payload.get("director_vision", "None")
        
        from core.service_registry import get_service
        editor_service = get_service("editor")
        capabilities_menu = editor_service.get_capabilities_menu()
        
        # Format prompt
        prompt = self.prompt_template.format(
            game_name=game_name,
            region=region,
            vibe=vibe,
            capabilities_menu=capabilities_menu
        )
        
        contents = [
            prompt,
            f"\n\n=== NARRATIVE SCRIPTS ===\n{scripts_context}",
            f"\n\n=== DIRECTOR VISION ===\n{director_vision}"
        ]
        
        # Generate Content
        from ..llm.llm_client import get_llm_client
        from google.genai import types
        
        client = get_llm_client("deepseek-v4-pro")
        gen_config = types.GenerateContentConfig(temperature=0.4)
        
        response_text = client.generate_content(
            model="deepseek-v4-pro",
            contents=contents,
            config=gen_config
        )
        
        return {"technical_directives": response_text}

