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
The `AIOrchestrator` (`backend/ai_director/orchestrator.py`) acts as the central brain and supervisor of the multi-agent AI assembly line. It is responsible for chunking the input video, generating context natively from raw high-quality chunks, and orchestrating the agents sequentially.

## The Chunking Strategy
To avoid overloading the LLM's token context window and to bypass DeepSeek API timeout limits, the AI Reviewer splits massive VODs into smaller overlapping chunks.
- **`split_video_with_overlap`**: Slices the video into e.g., 15-minute chunks with a 2-minute overlap using FFmpeg stream copying (`-c copy`).
- The pipeline processes each chunk entirely through all 6 agents independently, then merges the returned `shorts` variants and shifts their timestamps to be absolute relative to the original full-length VOD.

## The Context Engine
Before invoking any LLM, the `AIOrchestrator` executes hard-coded, deterministic Python scripts to provide **Pre-Generated Context**. This guarantees the AI has real-world data to anchor its narrative.
- **Audio Spikes**: `detect_audio_spikes` finds the top `N` loudest moments.
- **OCR Reading**: `read_ocr_from_video` grabs frames at those audio spikes and extracts the killfeed text.
- **Web Trends**: `fetch_regional_trends` scrapes external API data for algorithmic pacing logic.
- **Capabilities**: Pre-reads `index_local_sfx`, `index_local_music`, and `get_capabilities_menu`.
- **Semantic Matrix (NEW)**: `SemanticMatrixBuilder` runs local ONNX transformers (AST, SigLIP, Optical Flow) directly on the CPU to pre-calculate temporal "sheet music" of events, removing the need for a multimodal LLM.

## The `run_multi_agent_pipeline` Architecture (DAG)
The orchestrator has abandoned the rigid linear pipeline in favor of a **Directed Acyclic Graph (DAG)** to prevent "Lost in the Middle" hallucination:

### Transformer Pre-processing Stages
1. `clap_transformer` -> Uses Zero-Shot Audio Classification (CLAP) to process exact gaming foley (gunshots, footsteps) into audio timeline dicts.
2. `siglip_transformer` -> Classifies frames into visual timeline dicts.
3. `spatial_transformer` -> Calculates optical flow for dense spatial movement.
4. `matrix_merging` -> Concatenates and merges the above timelines into the unified Semantic Matrix JSON schema.

*(The orchestrator passes the resulting unified matrix to the LLM layer below).*

### Agent Execution Stages
1. `ObserverAgent` -> Parses the merged Semantic Matrix JSON and outputs the chronological descriptive log.
2. `ScriptWriterAgent` -> Takes log, outputs multi-variant templates.
3. `DirectorAgent` -> Takes log (NOT the script templates) to determine global visual vibe and music choice.
4. `EditorAgent` -> Merges both the Script templates and the Director's vibe into technical FFmpeg breakdowns.
5. `SpecialistAgent` -> Takes breakdowns + capabilities, validates math, outputs polished breakdown.
6. `BuilderAgent` -> Takes ONLY the polished breakdown, dropping the massive narrative context history entirely, and outputs a strict Pydantic JSON array.

### Error Handling & API Safety
- **Redrive Engine**: Jobs are explicitly tracked in the SQLite DB by `stage_name` and `chunk_id`. If a timeout occurs, the engine resumes exactly where it crashed.
- **Centralized LLM Error Handling**: The orchestrator relies entirely on the unified `LLMClient` which utilizes native `tenacity` exponential backoff, automatically unwrapping and logging rate limits (`429 Too Many Requests`) without requiring massive `try/except` chains at the pipeline level.
- **File Cleanup**: Upon a successful chunk processing, the raw chunk files are deleted to save storage space in the `workspace/` directory.
