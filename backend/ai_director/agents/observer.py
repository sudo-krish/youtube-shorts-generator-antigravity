from ai_director.config_manager import get_config
import logging
import json
from ai_director.llm_client import LLMClient
from google.genai import types

logger = logging.getLogger(__name__)

OBSERVER_PROMPT = """You are the Observer, an expert Esports commentator and YouTube Shorts producer. 
Instead of watching a raw video, you will be provided with a highly detailed Semantic Matrix Timeline (JSON object containing independent audio, visual, and spatial timelines) extracted by our local Audio/Video transformers. This matrix acts like "sheet music" for the gaming session.

Your job is to read this timeline matrix and extract a high-energy, vividly descriptive chronological text log. 

DO NOT just give me a dry play-by-play. I need you to narrate the STAKES, the MECHANICS, the EMOTION, and the CLUTCH POTENTIAL of every moment.

CRITICAL TRACKING REQUIREMENTS:
1. IDENTIFY THE POV PLAYER: Who is the person we are watching through the camera? What character/agent are they playing? What is their in-game name?
2. TRACK THE POV PLAYER EXPLICITLY: You MUST clearly distinguish between "The POV Player" and the rest of the lobby. Explicitly log when the POV PLAYER gets a kill, when the POV PLAYER misses a shot, or when the POV PLAYER dies.
3. STRICT ANTI-HALLUCINATION: NEVER hallucinate events. Do NOT exaggerate kills. Do NOT invent ACEs. Only report a kill if you VISUALLY see the kill feed icon or the enemy dying on screen. If you are not 100% sure, DO NOT report it.
4. EXTREME DETAIL DENSITY: Provide exact details for real action. Do not summarize a 15-second fight into one sentence. Detail the weapon used, exact movement, and outcome.
5. SPATIAL COORDINATES (DYNAMIC PANNING): For every key event, provide the start and end 2D approximate coordinate point `[start_x, end_x]` on a 1920x1080 grid where the core action/focus is located (e.g., `[960, 1200]`).

=== GLOBAL METADATA ===
Game: {game_name}
Region: {region}
Vibe: {vibe}

=== PRE-GENERATED CONTEXT ===
Audio Hype Map (Loudest Spikes): {audio_spikes}
Killfeed OCR Dumps at Spikes: {ocr_dumps}
Semantic Matrix Timeline: {semantic_matrix}

FORMAT YOUR RESPONSE EXACTLY LIKE THIS:
POV PLAYER IDENTITY: [Character Name] - [Player Name if visible]
[START_TIME_FLOAT - END_TIME_FLOAT] Focus:[start_x, end_x]: [Narrative Description] Describe the mechanics, who shot who, the outcome, the emotional tone, and WHY this moment is interesting. Ensure extreme second-by-second density.

Include every major engagement, death, funny moment, or fail. Timestamps MUST BE IN ABSOLUTE FLOAT SECONDS (e.g. 135.5 - 140.0). NEVER use MM:SS format!
Also append an "Intensity Heatmap" at the bottom rating the action density.
"""

class ObserverAgent:
    def execute(
        self,
        chunk_path: str,
        metadata: dict,
        audio_spikes: list,
        ocr_dumps: dict,
        semantic_matrix: list,
    ) -> str:
        logger.info("Observer Agent analyzing Semantic Matrix...")
        client = LLMClient()
        
        matrix_json = json.dumps(semantic_matrix, indent=2)

        prompt = OBSERVER_PROMPT.format(
            game_name=metadata.get("game_name", "Unknown"),
            region=metadata.get("region", "Global"),
            vibe=metadata.get("vibe", "Standard"),
            audio_spikes=audio_spikes,
            ocr_dumps=ocr_dumps,
            semantic_matrix=matrix_json,
        )

        return client.generate_content(
            model=get_config()["models"]["observer"],
            contents=[prompt],
            config=types.GenerateContentConfig(temperature=0.1),
        )

