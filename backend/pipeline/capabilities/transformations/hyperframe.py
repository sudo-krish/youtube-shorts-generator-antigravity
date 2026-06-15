import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)

def generate_crop_polynomial(video_path, target_w=1080):
    logger.info(f"Analyzing {video_path} for Hyperframe tracking...")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return f"(in_w-{target_w})/2"

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30
        
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    
    # Fallback if video is smaller than target
    if width <= target_w:
        cap.release()
        return "0"
    
    times = []
    x_coords = []
    
    ret, prev_frame = cap.read()
    if not ret:
        cap.release()
        return f"(in_w-{target_w})/2"
        
    # Resize for faster processing
    process_scale = 0.5
    prev_frame = cv2.resize(prev_frame, (0,0), fx=process_scale, fy=process_scale)
    prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
    prev_gray = cv2.GaussianBlur(prev_gray, (21, 21), 0)
    
    frame_idx = 1
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        frame = cv2.resize(frame, (0,0), fx=process_scale, fy=process_scale)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)
        
        diff = cv2.absdiff(prev_gray, gray)
        thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)
        
        contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            c = max(contours, key=cv2.contourArea)
            if cv2.contourArea(c) > 100: # Scaled down threshold
                M = cv2.moments(c)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    
                    # Scale back to original dimensions
                    cx = int(cx / process_scale)
                    
                    cx_clamped = max(target_w // 2, min(width - target_w // 2, cx))
                    
                    times.append(frame_idx / fps)
                    x_coords.append(cx_clamped - (target_w // 2))
                    
        prev_gray = gray
        frame_idx += 1
        
    cap.release()
    
    if len(times) < 10:
        logger.warning(f"Not enough motion detected in {video_path}, using static center crop.")
        return f"(in_w-{target_w})/2"
        
    # Fit 2nd degree polynomial (parabola) for ultra-smooth panning without oscillation
    # x = a*t^2 + b*t + c
    z = np.polyfit(times, x_coords, 2)
    a, b, c = z
    
    poly_str = f"({a:.4f}*t*t)+({b:.4f}*t)+({c:.4f})"
    clamped_str = f"min(in_w-{target_w}, max(0, {poly_str}))"
    
    logger.info(f"Generated Hyperframe polynomial for {video_path}: {clamped_str}")
    return clamped_str
