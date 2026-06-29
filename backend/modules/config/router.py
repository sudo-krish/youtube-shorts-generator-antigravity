from fastapi import APIRouter

router = APIRouter()

@router.get("")
async def stub_get():
    return {"status": "success", "data": "Not yet fully implemented."}

@router.post("")
async def stub_post():
    return {"status": "success", "data": "Not yet fully implemented."}
