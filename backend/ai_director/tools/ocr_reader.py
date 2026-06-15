import os
import tempfile
import subprocess
import logging

logger = logging.getLogger(__name__)

try:
    import pytesseract
    from PIL import Image
    HAS_OCR = True
except ImportError:
    HAS_OCR = False
    logger.warning("pytesseract or PIL not installed. OCR tool will gracefully degrade.")

def read_ocr_from_video(video_path: str, timestamps: list) -> dict:
    """
    Given a list of float timestamps, extracts a single frame at each timestamp
    and runs OCR to read the text (useful for killfeeds/scoreboards).
    Returns a dictionary of {timestamp: text}.
    """
    ocr_results = {}
    
    if not HAS_OCR or not timestamps:
        return ocr_results
        
    for ts in timestamps:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_img:
            temp_img_path = temp_img.name
            
        try:
            # Extract frame at exact timestamp
            cmd = [
                "ffmpeg", "-y", "-ss", str(ts), "-i", video_path,
                "-vframes", "1", "-q:v", "2", temp_img_path
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            
            # Run OCR
            img = Image.open(temp_img_path)
            text = pytesseract.image_to_string(img)
            
            if text.strip():
                ocr_results[ts] = text.strip()
            else:
                ocr_results[ts] = "[No readable text found]"
                
        except Exception as e:
            logger.error(f"OCR failed at {ts}s: {e}")
            ocr_results[ts] = "[OCR Error]"
        finally:
            if os.path.exists(temp_img_path):
                os.remove(temp_img_path)
                
    return ocr_results
