from fastapi import APIRouter

router = APIRouter()

@router.get("")
async def get_factory_status():
    from core.queue import render_queue
    return {"status": "success", "queue_size": render_queue.qsize()}
