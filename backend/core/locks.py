import asyncio
import logging

logger = logging.getLogger(__name__)

# Global lock to ensure VRAM-intensive transformers (YOLO, Llava) 
# don't run concurrently across different API endpoints and crash the 6GB VRAM.
vram_lock = asyncio.Lock()

async def acquire_vram_lock(transformer_name: str):
    logger.info(f"{transformer_name} is waiting for VRAM Lock...")
    await vram_lock.acquire()
    logger.info(f"{transformer_name} acquired VRAM Lock. Starting execution.")

def release_vram_lock(transformer_name: str):
    if vram_lock.locked():
        vram_lock.release()
        logger.info(f"{transformer_name} released VRAM Lock.")
