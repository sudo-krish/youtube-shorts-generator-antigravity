import asyncio
import os
from google.antigravity import Agent, LocalAgentConfig, GenerationConfig
from google.antigravity.types import from_file
from schemas import CategorizedClips
from dotenv import load_dotenv

load_dotenv()

PROMPT = """You are an expert viral gaming video editor. Watch this raw pure-gameplay footage. There is no voiceover.
You must rely entirely on visual cues (UI, health bars, combat intensity, screen text) to identify EVERY interesting moment in the video.

Categorize each moment into one of three buckets:
1. Proposition: The setup. Look for visual cues like entering a new area, a boss health bar appearing, or an objective updating on screen.
2. Struggle: The challenge. Look for high-intensity combat, the player taking heavy damage, near-death moments, or chaotic visual effects.
3. Result: The climax. Look for the enemy dying, a 'Victory' or 'Game Over' screen, or the player looting the reward.

Provide the exact start and end times for EVERY distinct clip you find in MM:SS format.
Crucially, identify up to 3 `visual_punch_in_timestamps` (exact absolute seconds, e.g. 15.5) for each clip where the visual intensity peaks (a massive hit, final blow, etc.). These will trigger automated camera zooms.
"""

async def main():
    try:
        config = LocalAgentConfig(
            model="gemini-2.5-pro",
            generation=GenerationConfig(
                response_schema=CategorizedClips,
                temperature=0.7
            )
        )
        print("Agent config created")
        async with Agent(config) as agent:
            print("Agent initialized successfully")
            file_location = os.path.join(os.path.dirname(__file__), "downloads", "dummy.mp4")
            video_asset = from_file(file_location)
            response = await agent.chat([video_asset, PROMPT])
            print("Response:", await response.text())
    except Exception as e:
        import traceback
        traceback.print_exc()

asyncio.run(main())
