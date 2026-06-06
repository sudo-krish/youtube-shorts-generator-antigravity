import asyncio
import os
from google.antigravity import Agent, LocalAgentConfig, GenerationConfig
from google.antigravity.types import from_file, UserMessage
from schemas import CategorizedClips
from dotenv import load_dotenv

load_dotenv()

PROMPT = "Explain what is in this video briefly."

async def main():
    config = LocalAgentConfig(
        model="gemini-1.5-flash",
    )
    try:
        async with Agent(config) as agent:
            file_location = os.path.join(os.path.dirname(__file__), "downloads", "dummy.mp4")
            if not os.path.exists(file_location):
                print(f"File {file_location} does not exist.")
                return
            video_asset = from_file(file_location)
            
            print("Calling agent.chat with UserMessage...")
            msg = UserMessage(content=[video_asset, PROMPT])
            response = await agent.chat(msg)
            print("Response:", await response.text())
    except Exception as e:
        import traceback
        traceback.print_exc()

asyncio.run(main())
