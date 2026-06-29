import os
import uuid
from core.db.manager import db
from .schema import DimGame, DimGameType, AudioKeyword
from sqlalchemy import select

class ToolsService:
    @staticmethod
    def get_supported_games() -> list:
        game_table = db.get_table(DimGame)
        type_table = db.get_table(DimGameType)
        
        with next(db.get_session()) as session:
            stmt = select(
                game_table.c.id, game_table.c.game_name, type_table.c.game_genre, 
                type_table.c.id.label("game_type_id"), game_table.c.folder_path
            ).select_from(
                game_table.join(type_table, game_table.c.game_type_id == type_table.c.id)
            ).order_by(game_table.c.game_name.asc())
            
            return [dict(r._mapping) for r in session.execute(stmt).fetchall()]

    @staticmethod
    def get_game_types() -> list:
        return db.filter(DimGameType, order_by="game_genre", descending=False)

    @staticmethod
    def get_audio_keywords(game_id: int) -> list:
        kw_table = db.get_table(AudioKeyword)
        game_table = db.get_table(DimGame)
        
        with next(db.get_session()) as session:
            stmt = select(kw_table.c.keyword).select_from(
                kw_table.join(game_table, game_table.c.game_type_id == kw_table.c.game_type_id)
            ).where(game_table.c.id == game_id)
            
            rows = session.execute(stmt).fetchall()
            return [row.keyword for row in rows]

    @staticmethod
    def get_game_context_path(game_id: int) -> str:
        game = db.get(DimGame, id=game_id)
        if game:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            return os.path.join(base_dir, game["folder_path"], 'context.txt')
        return None

    @staticmethod
    def create_game(game_name: str, game_type_id: int):
        game_uuid = str(uuid.uuid4())
        folder_path = os.path.join("assets", "games", game_uuid)
        abs_folder_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), folder_path)
        os.makedirs(abs_folder_path, exist_ok=True)
        with open(os.path.join(abs_folder_path, "context.txt"), "w") as f:
            f.write(f"Context and lore for {game_name}.\\n")
            
        db.create(DimGame, game_type_id=game_type_id, game_name=game_name, folder_path=folder_path)

tools_service = ToolsService()
