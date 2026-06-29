from pydantic import BaseModel, Field
from typing import Optional

class DimGameType(BaseModel):
    __tablename__ = "dim_game_types"
    id: Optional[int] = Field(default=None, json_schema_extra={"primary_key": True, "autoincrement": True})
    game_genre: str = Field(json_schema_extra={"unique": True})

class DimGame(BaseModel):
    __tablename__ = "dim_games"
    id: Optional[int] = Field(default=None, json_schema_extra={"primary_key": True, "autoincrement": True})
    game_type_id: int = Field(json_schema_extra={"index": True})
    game_name: str = Field(json_schema_extra={"unique": True})
    folder_path: str

class AudioKeyword(BaseModel):
    __tablename__ = "audio_keywords"
    id: Optional[int] = Field(default=None, json_schema_extra={"primary_key": True, "autoincrement": True})
    game_type_id: int = Field(json_schema_extra={"index": True})
    keyword: str
