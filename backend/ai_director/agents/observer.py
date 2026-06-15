from ai_director.config_manager import get_config
import logging
import google.genai as genai
from google.genai import types

logger = logging.getLogger(__name__)

OBSERVER_PROMPT = """You are the Observer, an expert Esports commentator and YouTube Shorts producer. Your job is to watch this raw gaming video chunk and extract a high-energy, vividly descriptive chronological text log. 

DO NOT just give me a dry play-by-play (e.g., "player walked here, player shot enemy"). I need you to narrate the STAKES, the MECHANICS, the EMOTION, and the CLUTCH POTENTIAL of every moment. Identify potential viral hooks, funny fails, or insane outplays.

CRITICAL TRACKING REQUIREMENTS:
1. IDENTIFY THE POV PLAYER: Who is the person we are watching through the camera? What character/agent are they playing? What is their in-game name?
2. TRACK THE POV PLAYER EXPLICITLY: You MUST clearly distinguish between "The POV Player" and the rest of the lobby. Explicitly log when the POV PLAYER gets a kill, when the POV PLAYER misses a shot, or when the POV PLAYER dies. The Scriptwriter relies on you to know exactly what happens to the main character.

=== GLOBAL METADATA ===
Game: {game_name}
Region: {region}
Vibe: {vibe}

=== PRE-GENERATED CONTEXT ===
Audio Hype Map (Loudest Spikes): {audio_spikes}
Killfeed OCR Dumps at Spikes: {ocr_dumps}

FORMAT YOUR RESPONSE EXACTLY LIKE THIS:
POV PLAYER IDENTITY: [Character Name] - [Player Name if visible]
[START_TIME - END_TIME]: [Narrative Description] Describe the mechanics, who shot who (especially if it was the POV player), the outcome, the emotional tone, and WHY this moment is interesting. 

Include every major engagement, death, funny moment, or fail. Timestamps MUST be in absolute float seconds (e.g. 15.5 - 20.0).
Also append an "Intensity Heatmap" at the bottom rating the action density."""

class ObserverAgent:
    def __init__(self):
        self.client = genai.Client()

    def execute(self, uploaded_file, metadata: dict, audio_spikes: list, ocr_dumps: dict) -> str:
        logger.info("Observer Agent analyzing raw video with pre-generated context...")
        
        prompt = OBSERVER_PROMPT.format(
            game_name=metadata.get("game_name", "Unknown"),
            region=metadata.get("region", "Global"),
            vibe=metadata.get("vibe", "Standard"),
            audio_spikes=audio_spikes,
            ocr_dumps=ocr_dumps
        )
        
        response = self.client.models.generate_content(
            model=get_config()["models"]["observer"],
            contents=[uploaded_file, prompt],
            config=types.GenerateContentConfig(temperature=0.7)
        )
        return response.text
