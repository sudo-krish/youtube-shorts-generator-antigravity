import asyncio

# Global async queue for the background render worker
render_queue = asyncio.Queue()
