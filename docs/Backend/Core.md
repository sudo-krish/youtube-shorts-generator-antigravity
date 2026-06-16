---
domain: Backend
folder_path: docs/Backend
description: "FastAPI orchestration, API endpoints, schemas, and config management."
veracity_score: 5
tags:
  - fastapi
  - endpoints
  - pydantic
  - config
---

# Backend Core Documentation

## Overview
The Antigravity backend is built using **FastAPI** (`backend/main.py`), acting as the orchestration layer for the multi-agent AI system and the FFmpeg pipeline. It manages incoming video uploads, triggers asynchronous processing jobs, streams real-time execution logs, and exposes API endpoints for the frontend UI.

## File Breakdown

### `main.py`
The primary entry point for the FastAPI application.
- **Initialization**: Sets up `WORKSPACE_DIR`, `SFX_DIR`, and `OUTPUTS_DIR`. Mounts the static workspace directory for frontend access.
- **WebSocket Streaming**: Exposes `/api/jobs/{job_id}/logs/stream` to stream live log files to the frontend UI so users can watch the AI's internal monologue in real-time.
- **Core Endpoints**:
  - `POST /api/upload`: Handles `.mp4` uploads, assigns a UUID, and saves the file to the workspace.
  - `POST /api/analyze`: Triggers the async orchestrator (`AIReviewer`) via FastAPI `BackgroundTasks`.
  - `POST /api/redrive/{job_id}`: Allows recovering a failed pipeline. It reads `job_stages` from the database, loads the `resume_state` cache from completed agents, and skips re-running expensive LLM API calls.
  - `POST /api/generate-short`: Dispatches a background rendering job. It loads the `_segments.json` blueprint and pushes tasks onto an `asyncio.Queue` worker (`render_worker()`).
  - `POST /api/jobs/{job_id}/render/batch`: Triggers batch rendering for multiple short variants simultaneously.
- **Workers**: Runs a persistent `render_worker()` async task to process FFmpeg rendering tasks sequentially.

### `ai_director/schemas.py`
Defines the rigid **Pydantic models** that force the LLM (specifically the Builder Agent) to output strict JSON.
- `VideoEffect`: Models individual FFmpeg effects (`effect_name`, `relative_start_time`, `duration`).
- `VideoPhase`: Models a discrete chunk of the video (start/end times, story text, spatial tracking coords, visual punch-ins).
- `ViralShortBlueprint`: Models a completed short variant, including the dynamically selected `background_audio_track`.
- `FactoryTimeline`: The root schema wrapping an array of `ViralShortBlueprint`s.

### `ai_director/config_manager.py`
Manages the global configuration for the AI models.
- **`config.json`**: Stores the user's selected LLM model names. By default, it maps the Observer to `gemini-2.5-flash`, the creative/builder agents to `deepseek-v4-flash` (Thinking disabled), and the mathematical/FFmpeg agents to `deepseek-v4-pro` (Reasoning enabled).
- Exposes `get_config()` and `set_config()` which are used by the `/api/config` endpoints in `main.py` to allow the frontend to change models on the fly.
