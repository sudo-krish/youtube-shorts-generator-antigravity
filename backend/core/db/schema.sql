PRAGMA journal_mode=WAL;

-- Videos Table
CREATE TABLE IF NOT EXISTS videos (
    video_id TEXT PRIMARY KEY,
    video_name TEXT UNIQUE,
    video_path TEXT,
    created_at REAL
);

-- Video Chunks Table
CREATE TABLE IF NOT EXISTS video_chunks (
    chunk_id TEXT PRIMARY KEY,
    video_id TEXT,
    chunk_index INTEGER,
    chunk_name TEXT,
    audio_chunk_name TEXT,
    start_time REAL,
    end_time REAL,
    FOREIGN KEY (video_id) REFERENCES videos (video_id)
);

-- Transformer Tests Table
CREATE TABLE IF NOT EXISTS transformer_tests (
    test_id TEXT PRIMARY KEY,
    video_id TEXT,
    chunk_index INTEGER,
    transformer_name TEXT,
    status TEXT,
    start_time REAL,
    end_time REAL,
    output_data TEXT,
    visual_output_path TEXT,
    FOREIGN KEY (video_id) REFERENCES videos (video_id)
);

-- Jobs Table
CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    video_id TEXT,
    status TEXT,
    metadata TEXT,
    num_chunks INTEGER DEFAULT 0,
    created_at REAL,
    json_path TEXT,
    FOREIGN KEY (video_id) REFERENCES videos (video_id)
);

-- Job Stages Table
CREATE TABLE IF NOT EXISTS job_stages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT,
    stage_name TEXT,
    status TEXT,
    logs TEXT,
    start_time REAL,
    end_time REAL,
    chunk_id INTEGER,
    model_id INTEGER,
    FOREIGN KEY (job_id) REFERENCES jobs (job_id),
    FOREIGN KEY (model_id) REFERENCES models (id)
);

-- Models Table
CREATE TABLE IF NOT EXISTS models (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT,
    model_name TEXT UNIQUE
);

-- Model Usage Table
CREATE TABLE IF NOT EXISTS model_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id INTEGER,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    cost REAL,
    timestamp REAL,
    FOREIGN KEY (model_id) REFERENCES models (id)
);

-- Rate Limits Table
CREATE TABLE IF NOT EXISTS rate_limits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id INTEGER,
    timestamp REAL,
    error_message TEXT,
    FOREIGN KEY (model_id) REFERENCES models (id)
);

-- Job Renders Table
CREATE TABLE IF NOT EXISTS job_renders (
    id TEXT PRIMARY KEY,
    job_id TEXT,
    variant_id TEXT,
    status TEXT,
    error_logs TEXT,
    outputs TEXT,
    created_at REAL,
    updated_at REAL,
    FOREIGN KEY (job_id) REFERENCES jobs (job_id)
);

-- Dim Game Types Table
CREATE TABLE IF NOT EXISTS dim_game_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_genre TEXT UNIQUE
);

-- Dim Games Table
CREATE TABLE IF NOT EXISTS dim_games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_type_id INTEGER,
    game_name TEXT UNIQUE,
    folder_path TEXT,
    FOREIGN KEY (game_type_id) REFERENCES dim_game_types (id)
);

-- Audio Keywords Table
CREATE TABLE IF NOT EXISTS audio_keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_type_id INTEGER,
    keyword TEXT,
    FOREIGN KEY (game_type_id) REFERENCES dim_game_types (id)
);
