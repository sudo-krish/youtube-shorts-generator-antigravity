---
domain: Backend
folder_path: docs/Backend
description: Backend services, APIs, and audio/video processing details.
veracity_score: 5
tags: [backend, api, python, modular, multi-agent, context, ffmpeg]
---

# Antigravity Studio - AI-Directed Video Engine

The powerhouse behind the Antigravity Shorts Engine. This FastAPI-driven backend runs a 6-Agent Template-Based Assembly Line to dynamically extract, script, direct, and edit massive gaming VODs into high-retention viral shorts. 

It is powered by a **Pre-Generated Context Engine**, ensuring the AI never hallucinates by pre-calculating real-world data (audio spikes, OCR, internet trends) using Python scripts before invoking the language models.

## The Multi-Agent Architecture & Context Engine

The rigid 3-part limit is gone. The backend now supports dynamic, N-Phase structures, driven by a sequence of specialized AI agents. To save tokens and eliminate hallucinations, we use **Python Pre-Processor Tools** (`backend/ai_director/tools/`) to generate context dumps *before* calling each agent:

### 1. Global UI Metadata Layer
The UI allows users to pass `Game Name`, `Region`, and `Player Vibe`. This metadata is injected into **every single agent's** prompt.

### 2. AI Director Assembly Line (`backend/ai_director/`)
Instead of one massive API prompt, the AI Director runs a sequential 6-agent pipeline:

- **Observer (`agents/observer.py`)**: Extracts raw chronological context.
  - *Pre-Generated Context*: **Audio Hype Map** & **OCR Killfeed Dump**.
  - *Tooling*: `tools/audio_hype.py` detects the loudest decibel spikes. `tools/ocr_reader.py` extracts the text on screen at those exact spikes so the Observer doesn't miss the action.
- **Script Writer (`agents/scriptwriter.py`)**: A Template Engine. Matches the footage against templates (Funny/Fail, Intense Clutch).
  - *Pre-Generated Context*: **Regional Web Trends**.
  - *Tooling*: `tools/web_scraper.py` simulates fetching trending cultural internet meta based on the UI Region metadata.
- **Director (`agents/director.py`)**: Injects "magic", defining emotional beats, vibes, and narrative text.
  - *Pre-Generated Context*: **Local SFX Library Menu**.
  - *Tooling*: `tools/sfx_indexer.py` provides an exact list of available `.mp3`/`.wav` files in the backend.
- **Editor (`agents/editor.py`)**: Translates the "magic" into concrete FFmpeg directives.
  - *Pre-Generated Context*: **Dynamic Capabilities Menu**.
  - *Tooling*: `capabilities/effects/registry.py` reads the metadata of all loaded FFmpeg visual/temporal effects and transitions.
- **YouTube Specialist (`agents/specialist.py`)**: Final Polish Editor. Validates timestamps, pacing, and hooks against algorithmic retention rules.
  - *Pre-Generated Context*: **YouTube Algorithm Rules** & **Math Validation Report**.
  - *Tooling*: `tools/math_validator.py` mathematically proves the Editor's timestamp math is physically possible. The Specialist automatically fixes any math errors and adds high-retention effects from the capabilities menu.
- **Builder (`agents/builder.py`)**: Formats the final, validated plans into a strict JSON blueprint array.

### 3. File Generator (`backend/generator/`)
A dedicated worker module.
- `cutter.py` takes the AI Blueprint and dynamically iterates over `N` phases, physically slicing the master VOD.
- `file_manager.py` organizes these raw clips into a single `outputs/{video_id}/` project folder.

### 4. Pipeline Editor (`backend/pipeline/`)
The executor module. 
- **XFade Engine (`engine.py`)**: Dynamically loops over the array of clips, generates action-tracking polygons via OpenCV, and stitches them together using complex **XFADE overlap cascades** instead of hard cuts. Allows for cinematic transitions (pixelize, wipeleft, fade).
- **Capabilities (`capabilities/`)**: Highly modularized editing techniques:
  - `audio/`: Background music mixing and decibel-spike sampling.
  - `effects/`: Visual elements like `VHS_Overlay`, `Motion_Blur`, `Dynamic_Glow`, `Deepfried`, and standard glitch/shake. Each effect exports rich metadata.
  - `transformations/`: The "Hyperframe" action-tracking polynomial cropper and smart zooms.
  - `text/`: Overlays including WhisperX word-by-word subtitles. Subtitles now feature ASS Macros for dynamic **scaling and popping** text animations (Alex Hormozi style).

## Database & Storage Architecture
- **Workspace Directory**: Video files, pipeline segments, and AI proxy videos are all dynamically generated and stored in `backend/workspace/`.
- **Relational Database**: State tracking is managed by a centralized SQLite database (`backend/runs.db` via `database.py`):
  - `videos`: Tracks physical files on disk via a `video_id` UUID.
  - `jobs`: Tracks execution Sessions, linking a `job_id` to a `video_id`, and safely stores job `metadata` as JSON.
  - `job_stages`: Tracks the hyper-granular states of the AI Assembly line (start times, end times, chunk logs, statuses).
- **Execution Logs**: Every job automatically writes isolated, cleanly formatted execution logs to `backend/outputs/logs/{session_id}.log`. All agent-level logs are routed through the global `"ai_director"` logger for highly detailed, readable outputs without UUID spam.
- **Redrive Capability**: When an agent fails (e.g. 503 from Gemini), you can safely redrive via `POST /api/redrive/{job_id}`. The redrive queries the `job_stages` table to determine completed steps and loads their cached outputs from `resume_state`. The state caches the output of *every* agent, including the Builder's final JSON schema, ensuring zero token waste on successfully completed agents.
- **Admin Control**: The backend exposes `GET /api/db/dump` and `DELETE /api/db/clear` to fetch the complete DB graph or perform a global wipe (which recursively cleans `outputs/agents/` and `workspace/` while leaving static assets untouched).

## Data Flow
`Master Video + UI Metadata -> Workspace -> Audio/OCR Pre-Processors -> The Observer -> Web Trends -> The Script Writer -> SFX Indexer -> The Director -> Capabilities Indexer -> The Editor -> Math Validator -> The YouTube Specialist -> JSON Output -> File Generator (Raw N-Phase Slices) -> XFade Pipeline Editor (Final Edited Variants)`
