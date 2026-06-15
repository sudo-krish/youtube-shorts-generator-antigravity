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
- It spins up a `concurrent.futures.ProcessPoolExecutor` to leverage multiple CPU cores and bypass the GIL.
- It processes each phase concurrently by cutting the video and immediately applying:
  - Global color grading (`eq=contrast=1.15:saturation=1.25:gamma=1.05`).
  - Spatial crop panning (calculating a cosine interpolation between `start_focus_x` and `end_focus_x` for dynamic subject tracking).
  - High-retention "Visual Punch-Ins" (zooming 115% instantly via `zoompan`).
  - Any isolated temporal or visual effects from the Capabilities Registry.

### Stage 2: XFADE Stitching
Once all chunks are pre-processed into isolated `.mp4` clips, they are stitched together chronologically.
- **Visual Stitching**: Hard cuts cause viewer drop-off. We use FFmpeg `xfade`. It overlaps the video streams by `0.5s` and applies cinematic transitions like `pixelize`, `fade`, or `wipeleft`. To prevent memory leaks and PTS desyncs, all video streams are strictly forced to `scale=1080:1920,fps=60` immediately before entering the `xfade` node.

### Stage 2.5: Demucs & Audio Ducking
- **Audio Stem Isolation**: The stitched audio is exported and passed through the **Demucs** ML model (`--two-stems=vocals`), completely isolating the player's voice from the chaotic game audio.
- **Audio Mix & Ducking**: Calls `build_audio_mix_filter` to apply dynamic music. It uses `sidechaincompress=threshold=0.08:ratio=4.0` feeding the background music **exclusively against the isolated vocal track**. This ensures BGM dips perfectly when the player speaks, but isn't crushed by loud game SFX like gunfire. It also overlays impact/whoosh SFX at specified visual punch-in timestamps using `adelay`.
- **LUFS Mastering**: A `loudnorm=I=-14:LRA=11:TP=-1.5` filter is appended to precisely master the audio to YouTube Shorts spec (-14 LUFS).

### Stage 3: WhisperX Caption Generation
- The stitched, mixed audio is passed to `run_whisperx()`.
- WhisperX runs a high-precision ASR model, aligns word-level timestamps, and generates a precise JSON array of timing coordinates instead of a static subtitle file.

### Stage 4: Final Assembly & Headless Composition
- The exact word timings are passed to the **Node.js Headless Compositor** (`index.js`).
- Puppeteer launches an off-screen HTML5 Canvas to render kinetic "Hormozi Pop" typography frame-by-frame into a transparent `.webm` video.
- A final, blazing fast FFmpeg pass uses the `overlay` filter to lay the transparent subtitle `.webm` over the main video stream and muxes the mastered audio.
- The temp chunks and `.wav` files are wiped from disk.
