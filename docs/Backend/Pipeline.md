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

The core rendering pipeline is completely decoupled into distinct, single-responsibility helper modules (e.g., `_extract_and_demucs_audio`, `_build_visual_filtergraph`, `_process_chunks_parallel`, and `_stitch_video_and_audio`) to prevent massive execution blocks.

To overcome FFmpeg's memory leaks and single-thread bottlenecks on massive graphs, the engine uses **Memory-Efficient Multi-Stage Chunk Rendering**.

## Execution Stages

### Stage 1: Parallel Pre-Processing of Chunks
Instead of building one monolithic 100-node FFmpeg filter graph (which crashes often), the engine iterates over the `N` phases defined in the JSON blueprint.
- It spins up a `concurrent.futures.ProcessPoolExecutor` to leverage multiple CPU cores and bypass the GIL.
- It processes each phase concurrently by cutting the video and immediately applying:
  - Global color grading (`eq=contrast=1.15:saturation=1.25:gamma=1.05`). A strict `limiter=min=0:max=255` is applied to prevent color space buffer overflows (neon artifacting) when combining intense visual filters.
  - Spatial crop panning (calculating a cosine interpolation between `start_focus_x` and `end_focus_x` for dynamic subject tracking).
  - High-retention "Visual Punch-Ins" (zooming 115% instantly via `zoompan`).
  - Any isolated temporal or visual effects from the Capabilities Registry.

### Stage 2: XFADE Stitching
Once all chunks are pre-processed into isolated `.mp4` clips, they are stitched together chronologically.
- **Visual Stitching**: Hard cuts cause viewer drop-off. We use FFmpeg `xfade`. It overlaps the video streams by `0.5s` and applies cinematic transitions like `pixelize`, `fade`, or `wipeleft`. To prevent memory leaks and PTS desyncs, all video streams are strictly forced to `scale=1080:1920,fps=60,settb=1/60000` immediately before entering the `xfade` node.

### Stage 2.5: Demucs & Audio Ducking
- **Audio Stem Isolation**: The stitched audio is exported and passed through the **Demucs** ML model (`--two-stems=vocals`), completely isolating the player's voice (`vocals.wav`) from the chaotic game audio (`no_vocals.wav`).
- **Audio Mix & Ducking**: Calls `build_audio_mix_filter` to apply dynamic music. It intelligently analyzes the RMS amplitude of `vocals.wav` using `numpy`/`scipy`—if silence is detected, it bypasses ducking to avoid zero-division crashes. Otherwise, it uses `sidechaincompress=threshold=0.08:ratio=4.0` feeding the background music **exclusively against the isolated vocal track**. This ensures BGM dips perfectly when the player speaks. It also overlays impact/whoosh SFX at specified visual punch-in timestamps using `adelay`.
- **Syntax Safe-Guards**: The builder safely strips trailing semi-colons to prevent FFmpeg crashes if no BGM/SFX tracks are scheduled for a specific variant.
- **LUFS Mastering**: A `loudnorm=I=-14:LRA=11:TP=-1.5` filter is appended to precisely master the audio to YouTube Shorts spec (-14 LUFS).

### Stage 3: WhisperX Caption Generation & Safety Locks
- The `temp_bg` and `temp_voc` tracks are physically remixed into a pure `raw_game_audio.wav` track to bypass any aggressive Demucs gating. This un-demucsed audio is passed to `run_whisperx()`.
- WhisperX runs a high-precision ASR model on CUDA, aligns word-level timestamps, and generates an Advanced SubStation Alpha (`.ass`) file with dynamic subtitle animations.
- **GPU Concurrency Safe-Guards**: WhisperX is wrapped in a strict `threading.Lock()` (`GPU_LOCK`). This ensures that multiple asynchronous jobs don't simultaneously hit the VRAM limit, preventing CUDA out-of-memory crashes on hardware with a 6GB VRAM ceiling. `torch.cuda.empty_cache()` is also explicitly called upon completion.
- **Language & Safe Zone Enforcement**: The transcription strictly enforces `language="en"` to prevent background noise hallucination (e.g., detecting "haw"). Furthermore, the subtitle `MarginV` is bounded to `450` pixels to avoid clashing with standard YouTube Shorts UI layouts.

### Stage 4: Final Assembly
- A final, blazing fast FFmpeg pass uses the `subtitles` video filter to burn the WhisperX `.ass` captions directly over the main video stream and muxes the mastered LUFS audio.
- The temp chunks and `.wav` files are cleanly wiped from disk.
