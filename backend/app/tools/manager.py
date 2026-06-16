# Central export file for tools
from .audio_hype import detect_audio_spikes
from .ocr_reader import read_ocr_from_video
from .web_scraper import fetch_regional_trends
from .sfx_indexer import index_local_sfx
from .audio_indexer import index_local_music
from .math_validator import validate_editor_math

__all__ = [
    "detect_audio_spikes",
    "read_ocr_from_video",
    "fetch_regional_trends",
    "index_local_sfx",
    "index_local_music",
    "validate_editor_math",
]
