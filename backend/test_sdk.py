import asyncio
from google.antigravity import Agent, LocalAgentConfig, GenerationConfig

async def main():
    config = LocalAgentConfig()
    async with Agent(config) as agent:
        response = await agent.chat("Hello world!")
        print("Response:", await response.text())
        print("Usage:", response.usage_metadata)

if __name__ == "__main__":
    asyncio.run(main())
