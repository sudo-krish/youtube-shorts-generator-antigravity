---
domain: Backend
folder_path: docs/Backend
description: "FFmpeg Engine documentation, multi-stage chunk rendering, XFADE, and audio ducking."
veracity_score: 5
tags:
  - ffmpeg
  - pipeline
  - xfade
  - rendering
---

# FFmpeg Pipeline Engine

## Overview
The `engine.py` script (`backend/pipeline/engine.py`) is the workhorse of the Antigravity backend. It translates the abstract JSON arrays into physical `.mp4` renders. 

To overcome FFmpeg's memory leaks and single-thread bottlenecks on massive graphs, the engine uses **Memory-Efficient Multi-Stage Chunk Rendering**.

## Execution Stages

### Stage 1: Parallel Pre-Processing of Chunks
Instead of building one monolithic 100-node FFmpeg filter graph (which crashes often), the engine iterates over the `N` phases defined in the JSON blueprint.
- It spins up a `concurrent.futures.ThreadPoolExecutor`.
- It processes each phase concurrently by cutting the video and immediately applying:
  - Global color grading (`eq=contrast=1.15:saturation=1.25:gamma=1.05`).
  - Spatial crop panning (calculating a cosine interpolation between `start_focus_x` and `end_focus_x` for dynamic subject tracking).
  - High-retention "Visual Punch-Ins" (zooming 115% instantly via `zoompan`).
  - Any isolated temporal or visual effects from the Capabilities Registry.

### Stage 2: XFADE Stitching & Audio Mix
Once all chunks are pre-processed into isolated `.mp4` clips, they are stitched together chronologically.
- **Visual Stitching**: Hard cuts cause viewer drop-off. We use FFmpeg `xfade`. It overlaps the video streams by `0.5s` and applies cinematic transitions like `pixelize`, `fade`, or `wipeleft`.
- **Audio Mix & Ducking**: Calls `build_audio_mix_filter` to apply dynamic music. It uses `sidechaincompress=threshold=0.08:ratio=4.0` to detect when the main audio track gets loud (e.g., player speaking), and automatically ducks the background music volume. It also overlays impact/whoosh SFX at specified visual punch-in timestamps using `adelay`.

### Stage 3: WhisperX Caption Generation
- The stitched, mixed audio (`_temp_mix.wav`) is passed to `run_whisperx()`.
- WhisperX runs a high-precision ASR model, aligns word-level timestamps, and generates a `.ass` (Advanced SubStation Alpha) subtitle file. This file contains complex typography animations.

### Stage 4: Final Assembly
- A final, blazing fast FFmpeg pass burns the `.ass` subtitles into the final video and muxes the audio streams.
- The temp chunks and `.wav` files are wiped from disk.
