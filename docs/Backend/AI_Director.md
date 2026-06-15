---
domain: Backend
folder_path: docs/Backend
description: "Multi-agent orchestrator, video chunking, and pre-generated context execution."
veracity_score: 5
tags:
  - orchestrator
  - ai
  - chunking
  - context
---

# Orchestration & Pipeline Reviewer

## Overview
The `AIReviewer` (`backend/ai_director/reviewer.py`) acts as the central brain and supervisor of the multi-agent AI assembly line. It is responsible for chunking the input video, creating lightweight AI proxy videos, generating context, and orchestrating the agents sequentially.

## The Chunking Strategy
To avoid overloading the LLM's token context window and to bypass Gemini API timeout limits, the AI Reviewer splits massive VODs into smaller overlapping chunks.
- **`split_video_with_overlap`**: Slices the video into e.g., 15-minute chunks with a 2-minute overlap using FFmpeg stream copying (`-c copy`).
- The pipeline processes each chunk entirely through all 6 agents independently, then merges the returned `shorts` variants and shifts their timestamps to be absolute relative to the original full-length VOD.

## The Context Engine
Before invoking any LLM, the `AIReviewer` executes hard-coded, deterministic Python scripts to provide **Pre-Generated Context**. This guarantees the AI has real-world data to anchor its narrative.
- **Audio Spikes**: `detect_audio_spikes` finds the top `N` loudest moments.
- **OCR Reading**: `read_ocr_from_video` grabs frames at those audio spikes and extracts the killfeed text.
- **Tracking**: `track_subject` runs a YOLOv8 pass over the chunk to dump the bounding box X-coordinates.
- **Web Trends**: `fetch_regional_trends` scrapes external API data for algorithmic pacing logic.
- **Capabilities**: Pre-reads `index_local_sfx`, `index_local_music`, and `get_capabilities_menu`.

## The `run_multi_agent_pipeline` Architecture (DAG)
The orchestrator has abandoned the rigid linear pipeline in favor of a **Directed Acyclic Graph (DAG)** to prevent "Lost in the Middle" hallucination:
1. `ObserverAgent` -> Parses video and outputs the chronological descriptive log.
2. `ScriptWriterAgent` -> Takes log, outputs multi-variant templates.
3. `DirectorAgent` -> Takes log (NOT the script templates) to determine global visual vibe and music choice.
4. `EditorAgent` -> Merges both the Script templates and the Director's vibe into technical FFmpeg breakdowns.
5. `SpecialistAgent` -> Takes breakdowns + capabilities, validates math, outputs polished breakdown.
6. `BuilderAgent` -> Takes ONLY the polished breakdown, dropping the massive narrative context history entirely, and outputs a strict Pydantic JSON array.

### Error Handling & API Safety
- **Redrive Engine**: Jobs are explicitly tracked in the SQLite DB by `stage_name` and `chunk_id`. If a timeout occurs, the engine resumes exactly where it crashed.
- **Sleep Loops**: The pipeline artificially pauses `time.sleep(60)` between major chunk executions to aggressively avoid Google Gemini's API rate limiting (`429 Too Many Requests`).
- **File Cleanup**: Upon a successful chunk processing, the proxy video and raw chunk files are deleted to save storage space in the `workspace/` directory.
