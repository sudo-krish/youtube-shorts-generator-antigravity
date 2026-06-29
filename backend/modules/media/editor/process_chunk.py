import logging
from core.base_service import BaseNanoService
from modules.media.editor.engine import process_chunk

logger = logging.getLogger(__name__)

class ProcessChunkService(BaseNanoService):
    """
    Nano-Service: POST /api/media/editor/process_chunk_lambda
    Processes a single clip into a fully cropped, color-graded, and zoomed chunk.
    Payload expected: {
        "idx": int,
        "clip_path": str,
        "meta": dict,
        "duration": float,
        "fps_fraction": str,
        "orig_w": int,
        "orig_h": int,
        "crop_w": int,
        "crop_h": int,
        "is_hook": bool,
        "hook_duration": float
    }
    """
    
    def execute(self, payload: dict) -> dict:
        logger.info(f"Processing chunk {payload.get('idx')}...")
        
        try:
            result = process_chunk(
                idx=payload.get("idx"),
                clip_path=payload.get("clip_path"),
                meta=payload.get("meta", {}),
                duration=payload.get("duration"),
                fps_fraction=payload.get("fps_fraction", "30/1"),
                orig_w=payload.get("orig_w", 1920),
                orig_h=payload.get("orig_h", 1080),
                crop_w=payload.get("crop_w", 1080),
                crop_h=payload.get("crop_h", 1920),
                is_hook=payload.get("is_hook", False),
                hook_duration=payload.get("hook_duration", 1.5)
            )
            return {"status": "success", "chunk_data": result}
        except Exception as e:
            logger.error(f"Chunk processing failed: {e}")
            return {"status": "error", "error": str(e)}
