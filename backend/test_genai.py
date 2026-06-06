import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def main():
    import google.genai as genai
    from google.genai import types
    print("genai imported successfully!")
    client = genai.Client()
    print("Client initialized:", client)

asyncio.run(main())
