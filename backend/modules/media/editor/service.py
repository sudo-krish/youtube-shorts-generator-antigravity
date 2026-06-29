import time
from core.db.manager import db
from modules.media.editor.schema import Video, VideoChunk, TransformerTest
from sqlalchemy import select, update

class EditorService:
    @staticmethod
    def create_video(video_id: str, video_name: str, video_path: str):
        db.create(Video, video_id=video_id, video_name=video_name, 
                  video_path=video_path, created_at=time.time())

    @staticmethod
    def get_video(video_id: str) -> dict:
        return db.get(Video, video_id=video_id)

    @staticmethod
    def get_video_by_path(video_path: str) -> dict:
        return db.get(Video, video_path=video_path)

    @staticmethod
    def get_all_videos() -> list:
        return db.filter(Video, order_by="created_at", descending=True)

    @staticmethod
    def create_chunk(chunk_id: str, video_id: str, chunk_index: int, chunk_name: str, 
                     audio_chunk_name: str, start_time: float, duration: float):
        db.create(VideoChunk, chunk_id=chunk_id, video_id=video_id, chunk_index=chunk_index,
                  chunk_name=chunk_name, audio_chunk_name=audio_chunk_name, 
                  start_time=start_time, end_time=start_time + duration)

    @staticmethod
    def get_chunk_by_index(video_id: str, chunk_index: int) -> dict:
        return db.get(VideoChunk, video_id=video_id, chunk_index=chunk_index)

    @staticmethod
    def update_audio_name(chunk_id: str, audio_chunk_name: str):
        db.update(VideoChunk, filters={"chunk_id": chunk_id}, updates={"audio_chunk_name": audio_chunk_name})

    @staticmethod
    def delete_chunk(chunk_id: str):
        db.delete(VideoChunk, chunk_id=chunk_id)

    @staticmethod
    def create_test(test_id: str, video_id: str, chunk_index: int, transformer_name: str):
        db.create(TransformerTest, test_id=test_id, video_id=video_id, 
                  chunk_index=chunk_index, transformer_name=transformer_name, 
                  status="running", start_time=time.time())

    @staticmethod
    def update_test(test_id: str, status: str, output_data: str = None, visual_path: str = None):
        updates = {"status": status, "end_time": time.time(), "output_data": output_data}
        if status in ('completed', 'success'):
            updates["visual_output_path"] = visual_path
        db.update(TransformerTest, filters={"test_id": test_id}, updates=updates)

    @staticmethod
    def get_all_tests() -> list:
        return db.filter(TransformerTest, order_by="start_time", descending=True)

    @staticmethod
    def get_capabilities_menu() -> str:
        from .edits.effects.registry import get_capabilities_menu
        return get_capabilities_menu()

editor_service = EditorService()
