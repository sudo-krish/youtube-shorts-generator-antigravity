import os
import json
import time
import math
import subprocess
import logging
import uuid
import ffmpeg

logger = logging.getLogger(__name__)

DOWNLOADS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")

class VideoOrchestrator:
    def __init__(self, video_path: str, prompt: str):
        self.video_path = video_path
        self.prompt = prompt

    def split_video_with_overlap(self, input_path: str, chunk_duration: int = 900, overlap: int = 120):
        logger.info(f"Splitting video with overlap: {input_path}")
        probe = ffmpeg.probe(input_path)
        duration = float(probe['format']['duration'])
        
        chunks = []
        start = 0
        idx = 1
        
        while start < duration:
            end = min(start + chunk_duration, duration)
            current_duration = end - start
            
            chunk_name = f"{os.path.splitext(os.path.basename(input_path))[0]}_chunk_{idx}.mp4"
            output_chunk_path = os.path.join(DOWNLOADS_DIR, chunk_name)
            
            # Using -copyts to attempt keeping absolute timestamps, but some containers reset.
            # We will handle timestamp offset manually just in case.
            cmd = [
                "ffmpeg", "-y", "-i", input_path,
                "-ss", str(start), "-t", str(current_duration),
                "-c", "copy", output_chunk_path
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            chunks.append(output_chunk_path)
            
            if end >= duration:
                break
                
            start += chunk_duration - overlap
            idx += 1
            
        logger.info(f"Generated {len(chunks)} chunks.")
        return chunks

    def deduplicate_fights(self, all_fights: list):
        logger.info("De-duplicating fights...")
        unique_fights = []
        
        # Sort by start_time to make proximity checking easier
        all_fights.sort(key=lambda x: x["proposition"]["start_time"])
        
        for fight in all_fights:
            prop_start = fight["proposition"]["start_time"]
            
            is_duplicate = False
            for uf in unique_fights:
                uf_start = uf["proposition"]["start_time"]
                if abs(prop_start - uf_start) <= 30.0:
                    is_duplicate = True
                    break
                    
            if not is_duplicate:
                unique_fights.append(fight)
                
        # Re-assign sequential IDs
        for idx, fight in enumerate(unique_fights, start=1):
            fight["fight_number"] = idx
            
        logger.info(f"Kept {len(unique_fights)} unique fights after de-duplication.")
        return unique_fights

    def create_ai_proxy(self, input_mp4: str) -> str:
        base_name = os.path.splitext(os.path.basename(input_mp4))[0]
        safe_name = str(uuid.uuid4())
        proxy_path = os.path.join(DOWNLOADS_DIR, f"{safe_name}_proxy.mp4")
        
        logger.info(f"Generating lightweight AI Proxy for {base_name}...")
        cmd = [
            "ffmpeg", "-y", "-i", input_mp4,
            "-vf", "fps=1,scale=-2:480", 
            "-c:v", "libx264", "-crf", "35", "-preset", "ultrafast",
            "-an", proxy_path
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return proxy_path

    def run_gemini_extraction(self, chunk_path: str):
        import google.genai as genai
        from google.genai import types
        from schemas import ViralShortsExtraction
        
        client = genai.Client()
        proxy_path = self.create_ai_proxy(chunk_path)
        
        logger.info(f"Uploading AI proxy for {os.path.basename(chunk_path)}...")
        uploaded_file = client.files.upload(file=proxy_path)
        
        while True:
            file_info = client.files.get(name=uploaded_file.name)
            if file_info.state.name == "ACTIVE":
                break
            elif file_info.state.name == "FAILED":
                raise Exception("Video processing failed in Gemini API.")
            logger.info("Waiting for video processing...")
            time.sleep(5)
            
        logger.info("Starting Gemini analysis...")
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[uploaded_file, self.prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ViralShortsExtraction,
                temperature=0.7,
            )
        )
        
        output_json = json.loads(response.text)
        
        try:
            client.files.delete(name=uploaded_file.name)
            if os.path.exists(proxy_path):
                os.remove(proxy_path)
            logger.info(f"Cleaned up temporary proxy files and Gemini API resources.")
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")
            
        return output_json.get("top_fights", [])

    def process_video_pipeline(self, job_status: dict, job_id: str):
        try:
            chunk_duration = 900
            overlap = 120
            
            if job_status and job_id:
                job_status[job_id]["progress"] = "Splitting video into chunks (this may take a moment)..."
                
            chunks = self.split_video_with_overlap(self.video_path, chunk_duration, overlap)
            
            all_fights = []
            start_offset = 0
            
            for idx, chunk in enumerate(chunks):
                progress_msg = f"Processing Chunk {idx+1} of {len(chunks)} via Gemini API..."
                logger.info(progress_msg)
                if job_status and job_id:
                    job_status[job_id]["progress"] = progress_msg
                
                fights = self.run_gemini_extraction(chunk)
                
                # Map chunk timestamps back to absolute video timestamps
                for fight in fights:
                    for phase in ["proposition", "struggle", "result"]:
                        if phase in fight:
                            fight[phase]["start_time"] += start_offset
                            fight[phase]["end_time"] += start_offset
                            
                all_fights.extend(fights)
                
                if idx < len(chunks) - 1:
                    sleep_msg = f"Respecting TPM limit. Sleeping for 60 seconds before Chunk {idx+2}..."
                    logger.info(sleep_msg)
                    if job_status and job_id:
                        job_status[job_id]["progress"] = sleep_msg
                    time.sleep(60)
                    
                start_offset += (chunk_duration - overlap)
                
                # Clean up the chunk mp4
                if os.path.exists(chunk):
                    os.remove(chunk)
                
            if job_status and job_id:
                job_status[job_id]["progress"] = "De-duplicating and finalizing timeline..."
                
            deduped = self.deduplicate_fights(all_fights)
            
            final_timeline = {"top_fights": deduped}
            
            if job_status and job_id:
                job_status[job_id]["status"] = "completed"
                job_status[job_id]["result"] = final_timeline
                
            return final_timeline
            
        except Exception as e:
            logger.error(f"Orchestrator failed: {str(e)}")
            if job_status and job_id:
                job_status[job_id]["status"] = "failed"
                job_status[job_id]["progress"] = f"Failed: {str(e)}"
            raise e
