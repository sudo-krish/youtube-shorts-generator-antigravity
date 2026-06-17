import cv2
import os
import logging

logger = logging.getLogger(__name__)

def create_yolo_overlay_video(input_video_path: str, output_video_path: str, matrix_data: list):
    """
    Reads an MP4, draws YOLO bounding boxes per frame based on the transformer matrix,
    and saves the resulting MP4.
    matrix_data format: [{"t_float": 0.0, "boxes": [{"label": "Head", "x": 100, "y": 200, "w": 50, "h": 50, "conf": 0.9}]}, ...]
    """
    if not os.path.exists(input_video_path):
        raise FileNotFoundError(f"Video not found: {input_video_path}")

    cap = cv2.VideoCapture(input_video_path)
    if not cap.isOpened():
        raise Exception(f"Failed to open video: {input_video_path}")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    temp_path = output_video_path + ".temp.mp4"
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(temp_path, fourcc, fps, (width, height))

    # Create a quick lookup for bounding boxes by integer second
    box_lookup = {}
    for entry in matrix_data:
        t_int = int(entry.get("t_float", 0))
        box_lookup[t_int] = entry.get("boxes", [])

    frame_count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        current_second = int(frame_count / fps)
        
        boxes = box_lookup.get(current_second, [])
        for box in boxes:
            label = box.get("label", "Unknown")
            center_x = int(box.get("x", 0))
            center_y = int(box.get("y", 0))
            w = int(box.get("w", 0))
            h = int(box.get("h", 0))
            conf = box.get("confidence", box.get("conf", 0.0))

            color = (0, 255, 0) if label in ("enemy", "Head") else (255, 0, 0)
            
            # Calculate top-left and bottom-right from center coordinates
            x1 = int(center_x - w / 2)
            y1 = int(center_y - h / 2)
            x2 = int(center_x + w / 2)
            y2 = int(center_y + h / 2)
            
            # Draw rectangle
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            
            # Draw label
            text = f"{label} {conf:.2f}"
            cv2.putText(frame, text, (x1, max(15, y1 - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        out.write(frame)
        frame_count += 1

    cap.release()
    out.release()
    
    # Convert to H.264 so web browsers can play it natively
    import subprocess
    subprocess.run(["ffmpeg", "-y", "-i", temp_path, "-vcodec", "libx264", "-acodec", "aac", output_video_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists(temp_path):
        os.remove(temp_path)
    
    logger.info(f"YOLO Overlay Video saved to {output_video_path}")
