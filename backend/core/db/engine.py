import os
import logging
from sqlalchemy import create_engine, MetaData, Table, Column, String, Integer, Float, Boolean
from sqlalchemy.orm import sessionmaker
from core.db.registry import REGISTERED_SCHEMAS

logger = logging.getLogger(__name__)

# Base path setup
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Determine DB backend from ENV, default to SQLite
DB_BACKEND = os.environ.get("DB_BACKEND", "sqlite")

if DB_BACKEND == "sqlite":
    DB_PATH = os.path.join(_BASE_DIR, "antigravity.db")
    DATABASE_URL = f"sqlite:///{DB_PATH}"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
elif DB_BACKEND == "postgres":
    DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://user:password@localhost/dbname")
    engine = create_engine(DATABASE_URL)
else:
    # Fallback to SQLite
    DB_PATH = os.path.join(_BASE_DIR, "antigravity.db")
    DATABASE_URL = f"sqlite:///{DB_PATH}"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

metadata = MetaData()

def get_sqlalchemy_type(type_annotation):
    type_str = str(type_annotation).lower()
    if 'int' in type_str:
        return Integer
    elif 'float' in type_str:
        return Float
    elif 'bool' in type_str:
        return Boolean
    else:
        return String

# Dynamically parse Pydantic schemas to SQLAlchemy Tables
generated_tables = {}

for tablename, pydantic_model in REGISTERED_SCHEMAS.items():
    columns = []
    for name, field in pydantic_model.model_fields.items():
        col_type = get_sqlalchemy_type(field.annotation)
        
        extra = getattr(field, 'json_schema_extra', {}) or {}
        is_pk = extra.get('primary_key', False)
        is_index = extra.get('index', False)
        is_unique = extra.get('unique', False)
        is_auto = extra.get('autoincrement', False)
        
        columns.append(Column(
            name, 
            col_type, 
            primary_key=is_pk, 
            index=is_index, 
            unique=is_unique, 
            autoincrement=is_auto
        ))
        
    table = Table(tablename, metadata, *columns)
    generated_tables[tablename] = table

def init_db():
    if DB_BACKEND in ["sqlite", "postgres"]:
        logger.info(f"Initializing {DB_BACKEND} database. Creating tables...")
        metadata.create_all(engine)
    elif DB_BACKEND == "dynamodb":
        logger.info("DynamoDB backend active. Skipping SQLAlchemy migration.")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
