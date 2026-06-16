---
domain: "Backend"
folder_path: "docs/Backend"
description: "The directory structure and domain boundaries of the FastAPI backend."
veracity_score: 5
tags:
  - backend
  - structure
  - modules
---

# FastAPI Backend Application Structure

The backend follows a Django-style domain-driven architecture. The core principle is that `main.py` remains incredibly thin, acting only as the entrypoint. All business logic, REST controllers, and models are separated into bounded contexts within `app/`.

## Directory Map

```
backend/
├── main.py                     # Thin entrypoint (FastAPI instantiation, CORS, Root Router)
├── api/
│   ├── router.py               # The central "urls.py". Aggregates all app/ domain routers.
│   └── schemas.py              # Aggregated Pydantic schemas (if globally shared).
├── core/
│   ├── db/                     # Database abstraction (ORM layer).
│   │   ├── manager.py          # The `db` singleton containing Video, Job, Chunk managers.
│   │   ├── connection.py       # Thread-safe SQLite WAL connection pooling.
│   │   └── schema.sql          # Source-of-truth DDL statements.
│   ├── middleware.py           # API Middlewares (CORS, timing).
│   ├── queue.py                # Global Asyncio Queues (e.g., render_queue) to prevent circular imports.
│   └── locks.py                # GPU/VRAM concurrency semaphores.
└── app/                        # Domain-Driven Applications
    ├── admin/                  # System configuration, metrics, and global db triggers.
    ├── agents/                 # AI Persona prompts and workflow implementations (Scriptwriter, Editor).
    ├── audio_extractor/        # Tooling for slicing .wav from .mp4 handles.
    ├── chunking/               # Splitting massive VODs into processable semantic blocks.
    ├── generator/              # FFmpeg rendering, capabilities routing, and filtergraph generation.
    ├── orchestrator/           # The background async DAG manager, WebSockets, and LLM Client.
    ├── testing/                # Endpoints specifically designed for the UI's transformer testing.
    ├── tools/                  # Deterministic pre-processors (OCR, Audio Hype tracking).
    ├── transformers/           # Machine Learning wrappers (SigLIP, VideoMAE, Whisper).
    └── upload/                 # Ingestion endpoints for raw video files.
```

## Routing Pattern
When creating a new endpoint:
1. Locate the correct domain folder in `app/` (e.g., `app/upload/`).
2. Define the route in `app/upload/router.py` using `router = APIRouter()`.
3. Include the router in `api/router.py`.

## The `core/db` Pattern
All raw SQL queries must be placed inside the `backend/core/db/manager.py` file. Endpoint controllers and background tasks must use the `db` singleton (`from core.db.manager import db`) and interact via Python methods (e.g., `db.jobs.update_status(job_id, "processing")`).
