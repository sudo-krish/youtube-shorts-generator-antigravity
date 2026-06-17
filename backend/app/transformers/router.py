from fastapi import APIRouter, HTTPException
import logging
from app.transformers.schemas import TransformerRequest, TransformerResponse
from core.locks import acquire_vram_lock, release_vram_lock
from app.transformers.audio_voxtral import AudioVoxtralTransformer
from app.transformers.video_llava import LlavaVideoTransformer as VisionTransformer
from app.transformers.spatial_videomae import SpatialFlowTransformer as SpatialTransformer
from app.transformers.yolo_tracker import YoloPlayerTracker
from core.settings import get_asset_path

router = APIRouter(tags=["transformers"])
logger = logging.getLogger(__name__)

@router.post("/audio", response_model=TransformerResponse)
async def run_audio_transformer(req: TransformerRequest):
    logger.info(f"API: Running Audio Transformer on {req.video_path}")
    await acquire_vram_lock("AudioTransformer")
    matrix = []
    transformer = AudioVoxtralTransformer(game_id=req.game_id)
    transformer.load_model()
    try:
        for t in np.arange(0, req.duration, req.step):
            audio_context = transformer.process(req.video_path, float(t), float(t + req.step))
            matrix.append({"t_float": float(t), "audio_context": audio_context})
    finally:
        transformer.unload_model()
        release_vram_lock("AudioTransformer")
    return TransformerResponse(matrix=matrix)

import numpy as np

@router.post("/vision", response_model=TransformerResponse)
async def run_vision_transformer(req: TransformerRequest):
    logger.info(f"API: Running Vision Transformer on {req.video_path}")
    await acquire_vram_lock("VisionTransformer")
    matrix = []
    transformer = VisionTransformer()
    transformer.load_model()
    try:
        previous_context = []
        for t in np.arange(0, req.duration, req.step):
            visual_tags = transformer.process(
                req.video_path, 
                float(t), 
                float(t + req.step), 
                previous_context=previous_context,
                game_name=req.game_id or ""
            )
            if visual_tags and isinstance(visual_tags, list) and len(visual_tags) > 0:
                previous_context.append(visual_tags[0])
            matrix.append({"t_float": float(t), "visual_tags": visual_tags})
    finally:
        transformer.unload_model()
        release_vram_lock("VisionTransformer")
    return TransformerResponse(matrix=matrix)

@router.post("/spatial", response_model=TransformerResponse)
async def run_spatial_transformer(req: TransformerRequest):
    logger.info(f"API: Running Spatial Transformer on {req.video_path}")
    matrix = []
    transformer = SpatialTransformer()
    transformer.load_model()
    try:
        for t in np.arange(0, req.duration, req.step):
            spatial_tags = transformer.process(req.video_path, float(t), float(t + req.step))
            matrix.append({"t_float": float(t), "spatial_tags": spatial_tags})
    finally:
        transformer.unload_model()
    return TransformerResponse(matrix=matrix)

@router.post("/yolo", response_model=TransformerResponse)
async def run_yolo_transformer(req: TransformerRequest):
    logger.info(f"API: Running YOLO Transformer on {req.video_path}")
    await acquire_vram_lock("YoloTransformer")
    matrix = []
    model_p = get_asset_path("yoloe-26s-seg.pt", "model")
    tracker = YoloPlayerTracker(model_path=model_p)
    tracker.load_model()
    try:
        for t in np.arange(0, req.duration, req.step):
            boxes = tracker.process(req.video_path, float(t), float(t + req.step))
            matrix.append({"t_float": float(t), "boxes": boxes})
    finally:
        tracker.unload_model()
        release_vram_lock("YoloTransformer")
    return TransformerResponse(matrix=matrix)
