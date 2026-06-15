from ai_director.config_manager import get_config
import logging
import json
import google.genai as genai
from google.genai import types

logger = logging.getLogger(__name__)

OBSERVER_PROMPT = """You are the Observer, an expert Esports commentator and YouTube Shorts producer. Your job is to watch this raw gaming video chunk and extract a high-energy, vividly descriptive chronological text log. 

DO NOT just give me a dry play-by-play (e.g., "player walked here, player shot enemy"). I need you to narrate the STAKES, the MECHANICS, the EMOTION, and the CLUTCH POTENTIAL of every moment. Identify potential viral hooks, funny fails, or insane outplays.

CRITICAL TRACKING REQUIREMENTS:
1. IDENTIFY THE POV PLAYER: Who is the person we are watching through the camera? What character/agent are they playing? What is their in-game name?
2. TRACK THE POV PLAYER EXPLICITLY: You MUST clearly distinguish between "The POV Player" and the rest of the lobby. Explicitly log when the POV PLAYER gets a kill, when the POV PLAYER misses a shot, or when the POV PLAYER dies. The Scriptwriter relies on you to know exactly what happens to the main character.
3. ANTI-HALLUCINATION: NEVER hallucinate events. Do NOT exaggerate kills. If the pre-generated killfeed context or visual evidence does not explicitly confirm 5 kills by the POV player, DO NOT use the word ACE. Base your narrative STRICTLY on concrete evidence.
4. EXTREME DETAIL DENSITY: You must provide extreme detail for EVERY SECOND of action. Do not summarize a 15-second fight into one sentence. Detail the weapon used, the exact movement, exact outcome, and screen events (e.g. "Reyna peeks left, misses 3 Vandal shots, dashes back").
5. SPATIAL COORDINATES (DYNAMIC PANNING): For every key event, provide the start and end 2D approximate coordinate point `[start_x, end_x]` on a 1920x1080 grid where the core action/focus is located (e.g., `[960, 1200]` if the player flicks from center to right). Always include this for kills, deaths, or points of interest.

=== GLOBAL METADATA ===
Game: {game_name}
Region: {region}
Vibe: {vibe}

=== PRE-GENERATED CONTEXT ===
Audio Hype Map (Loudest Spikes): {audio_spikes}
Killfeed OCR Dumps at Spikes: {ocr_dumps}
AI Object Tracking Data (Smoothed X Coordinates over Time): {tracking_data}

FORMAT YOUR RESPONSE EXACTLY LIKE THIS:
POV PLAYER IDENTITY: [Character Name] - [Player Name if visible]
[START_TIME - END_TIME] Focus:[start_x, end_x]: [Narrative Description] Describe the mechanics, who shot who (especially if it was the POV player), the outcome, the emotional tone, and WHY this moment is interesting. Ensure extreme second-by-second density.

Include every major engagement, death, funny moment, or fail. Timestamps MUST be in absolute float seconds (e.g. 15.5 - 20.0).
Also append an "Intensity Heatmap" at the bottom rating the action density."""

class ObserverAgent:
    def __init__(self):
        self.client = genai.Client()

    def execute(self, uploaded_file, metadata: dict, audio_spikes: list, ocr_dumps: dict, tracking_data: list) -> str:
        logger.info("Observer Agent analyzing raw video with pre-generated context...")
        
        prompt = OBSERVER_PROMPT.format(
            game_name=metadata.get("game_name", "Unknown"),
            region=metadata.get("region", "Global"),
            vibe=metadata.get("vibe", "Standard"),
            audio_spikes=audio_spikes,
            ocr_dumps=ocr_dumps,
            tracking_data=json.dumps(tracking_data) if tracking_data else "None"
        )
        
        response = self.client.models.generate_content(
            model=get_config()["models"]["observer"],
            contents=[uploaded_file, prompt],
            config=types.GenerateContentConfig(temperature=0.7)
        )
        return response.text
