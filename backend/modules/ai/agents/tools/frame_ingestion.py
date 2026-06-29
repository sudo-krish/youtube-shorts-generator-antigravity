import os
import cv2
import logging
from core.db.manager import db
from modules.ai.schema import JobIngestionState

class FrameIngestionEngine:
    """
    Pillar 1: The Producer
    Strictly turns videos into queued image data.
    """
    
    def __init__(self, fps_extraction: float = 5.0):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.fps_extraction = fps_extraction

    def process(self, video_path: str, job_id: str) -> str:
        """
        Extracts images at the specified FPS and saves them to a temp directory.
        Updates the ingestion state in the DB to remain fail-safe.
        Returns the output directory.
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video not found: {video_path}")
            
        out_dir = f"/tmp/jobs/{job_id}/frames"
        os.makedirs(out_dir, exist_ok=True)
        
        cap = cv2.VideoCapture(video_path)
        video_fps = cap.get(cv2.CAP_PROP_FPS)
        if video_fps <= 0:
            video_fps = 30.0
            
        step_frames = max(1, int(video_fps / self.fps_extraction))
        current_frame = 0
        extracted_count = 0
        
        self.logger.info(f"Ingesting {video_path} for job {job_id} at {self.fps_extraction} FPS")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            if current_frame % step_frames == 0:
                timestamp = current_frame / video_fps
                out_path = os.path.join(out_dir, f"frame_{timestamp:.2f}.jpg")
                cv2.imwrite(out_path, frame)
                extracted_count += 1
                
                # Update fail-safe state in DB
                self._update_state(job_id, timestamp)
                
            current_frame += 1
            
        cap.release()
        self.logger.info(f"Ingestion complete for job {job_id}. Extracted {extracted_count} frames.")
        return out_dir
        
    def _update_state(self, job_id: str, timestamp: float):
        try:
            with next(db.get_session()) as session:
                state = session.query(JobIngestionState).filter_by(job_id=job_id).first()
                if not state:
                    state = JobIngestionState(job_id=job_id, last_processed_timestamp=timestamp)
                    session.add(state)
                else:
                    state.last_processed_timestamp = timestamp
                session.commit()
        except Exception as e:
            self.logger.warning(f"Failed to update ingestion state for {job_id}: {e}")
