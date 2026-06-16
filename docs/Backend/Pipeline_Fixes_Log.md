---
domain: Backend
folder_path: docs/Backend
description: "Historical log of all pipeline bug fixes, performance bottlenecks, and architectural decisions to prevent regressions."
veracity_score: 5
tags:
  - changelog
  - pipeline
  - fixes
  - architecture
---

# Pipeline Fixes & Architecture Log

This document serves as the **historical memory** for the Antigravity Engine's rendering pipeline. It tracks major bugs, bottlenecks, and the precise architectural decisions implemented to fix them. **Always consult this log before refactoring pipeline code** to prevent re-introducing past bugs.

---

## June 2026: The "Pipeline Resiliency" Update

During a major stress test of the AI generation and FFmpeg rendering pipeline, several severe bottlenecks and crashes were identified and resolved.

### 1. SQLite Concurrency Deadlocks
- **The Bug:** Running multi-agent generative tasks and concurrent background chunk rendering caused `sqlite3.OperationalError: database is locked` exceptions, crashing the API.
- **The Decision:** Migrated all database connections to use `check_same_thread=False` and a `timeout=15.0`. Crucially, added `PRAGMA journal_mode=WAL;` (Write-Ahead Logging) on database initialization. 
- **Rule:** Never revert to standard SQLite rollback journals. WAL is strictly required for the Fastapi background tasks to run concurrently without deadlocks.

### 2. WhisperX CUDA Out-Of-Memory (VRAM Overlap)
- **The Bug:** Multiple jobs triggering `whisperx.load_model()` concurrently overwhelmed the host system's strict 6GB VRAM limit, causing hard crashes.
- **The Decision:** Wrapped the WhisperX invocation in a strict global `threading.Lock()` named `GPU_LOCK` inside `overlays.py`. Enforced `device="cuda"` if available, and explicitly appended `torch.cuda.empty_cache()` to flush VRAM after transcription.
- **Rule:** Never remove the thread lock around heavy ML inference boundaries, even if it forces sequential execution. Stability > Parallelism.

### 3. WhisperX Language Hallucination
- **The Bug:** During silent or purely game-SFX audio chunks, WhisperX would occasionally hallucinate the language (e.g., detecting `haw` for Hawaiian) and fail to load the alignment dictionary.
- **The Decision:** Forced `language="en"` natively inside the `model.transcribe()` call and the `whisperx.load_align_model()` call. 
- **Rule:** Do not allow WhisperX to auto-detect language unless the channel's target demographic changes.

### 4. Demucs Silence Division-By-Zero
- **The Bug:** If Demucs processed a chunk with absolutely zero vocal frequencies, it exported a purely silent `vocals.wav`. Feeding a silent sidechain into FFmpeg's `sidechaincompress` filter caused a pipeline hang or crash.
- **The Decision:** Imported `numpy` and `scipy.io.wavfile` in `mixing.py` to analyze the exact RMS amplitude of the `vocals.wav` file. If the maximum amplitude is below a threshold (e.g., `500`), the sidechain compressor is entirely bypassed, and a flat `-10dB` duck is applied to the background track instead.
- **Rule:** Never pass untrusted or potentially empty audio streams into advanced dynamic range compression nodes without validating their energy first.

### 5. Color Space Buffer Overflows (Neon Artifacting)
- **The Bug:** Stacking visual effects (like `Deepfried` + `Dynamic_Glow` + `Contrast 1.15`) pushed RGB values beyond their maximum boundaries, resulting in corrupt neon green/black artifact frames.
- **The Decision:** Appended a strict `format=yuv420p,limiter=min=0:max=255` string to the end of the global `_build_visual_filtergraph` chain in `engine.py`.
- **Rule:** The limiter must ALWAYS be the absolute last filter in the visual chain before outputting to a stream.

### 6. Subtitle Safe-Zone Clashes
- **The Bug:** YouTube Shorts updated their bottom description/UI layout. The legacy `MarginV=150` on the WhisperX `.ass` generated subtitles pushed the captions too far down, colliding with the native app UI.
- **The Decision:** Increased the `.ass` `MarginV` from `150` to `450` in `overlays.py`.
- **Rule:** Typography must remain strictly clamped to the 30% - 60% vertical safe-zone quadrant on a 1080x1920 canvas.

### 7. XFADE Timebase Desyncs
- **The Bug:** Transitioning between `.mp4` chunks with differing framerates or timebases caused the FFmpeg `xfade` filter to drift audio/video sync, holding massive frame buffers and leaking RAM.
- **The Decision:** Appended `settb=1/60000` to the universal `scale=1080:1920,fps=60` input formatters directly before the `xfade` nodes.
- **Rule:** All inputs to `xfade` must have matching resolutions, framerates, and identical explicit timebases.

### 8. Visual Squish Distortion (Aspect Ratio Ignoring)
- **The Bug:** Applying `scale=1080:1920` to a 16:9 gaming clip directly squished the image horizontally.
- **The Decision:** Enforced a `crop=608:1080` parameter *before* the scaling node, and used trigonometric cosine interpolation between the AI's coordinates to pan across the cropped bounding box smoothly.

### 9. DeepSeek `<think>` Tag Injection
- **The Bug:** DeepSeek R1 models occasionally leaked their raw internal reasoning chain (`<think>...</think>`) into the final JSON output, breaking standard `json.loads`.
- **The Decision:** Implemented a robust `re.sub` regex stripper in `llm_client.py` to blindly eradicate `<think>` blocks before attempting to parse strings.

### 10. Center-Anchored Spatial Tracking (The Right-Crop Bug)
- **The Bug:** Applying `x=start_focus_x` caused the crop box origin to begin at the subject, meaning the subject was entirely pushed to the extreme left and often cropped out.
- **The Decision:** Implemented a pure trigonometric FFmpeg equation: `max(0, min({orig_w}-{crop_w}, ({start_focus_x} - {half_crop}) + ...))` to properly center the subject within the 9:16 crop box.

### 11. Vertical Axis (Y) Hardcoding Drift
- **The Bug:** Applying `y=0` to the crop expression pinned 1080p crops to the absolute top of the screen, severely cutting off the bottom half of 1440p gaming footage.
- **The Decision:** Modified the expression to dynamically center the crop vertically based on source resolution: `y='(ih-1080)/2'`.

### 12. Un-Demucsed Audio for WhisperX (The 2-Word Subtitle Bug)
- **The Bug:** Demucs vocal isolation occasionally misclassified distorted headset mics as "background noise," deleting the player's voice. Since WhisperX ran *after* Demucs, it generated 2-word captions.
- **The Decision:** `engine.py` now recombines the separated `temp_bg` and `temp_voc` via an `amix` filter into a pure `raw_game_audio.wav` *before* the BGM is applied. WhisperX operates purely on this raw track.

### 13. Sequential Phase Audio Echo (Contiguous Handles)
- **The Bug:** Slicing a continuous 60-second video into two contiguous 30-second phases and padding both with 3-second handles caused the audio to overlap and echo when XFADE restitched them.
- **The Decision:** `cutter.py` now natively tracks the `previous_phase`. If `current_phase.start_time == previous_phase.end_time`, `HANDLE_DURATION` is forced to `0.0`, eliminating echo while maintaining chronological visual progression.

### 14. VAD TensorFloat-32 (TF32) Underutilization
- **The Bug:** Pyannote VAD execution was not leveraging the host GPU's Tensor Cores efficiently.
- **The Decision:** Added `torch.backends.cuda.matmul.allow_tf32 = True` and `torch.backends.cudnn.allow_tf32 = True` to the FastAPI entry point.

### 15. QA Gate Audio False Positives
- **The Bug:** The structural QA check was blindly passing videos that contained broken or silent audio tracks if the video variance was fine.
- **The Decision:** Integrated an `astats` check in `qa_gate.py` that extracts the `lavfi.astats.Overall.RMS_level` frame tags. If the mean RMS volume is `<-50dB`, the gate intentionally fails the render.

### 16. Hook-to-Body PTS Stitching Desync
- **The Bug:** Concatenating a 3-second hook to a 45-second body without resetting Presentation Timestamps (PTS) caused severe audio/video drift.
- **The Decision:** Appended `asetpts=PTS-STARTPTS` to the hook's audio trim filtergraph inside `tree_generator.py`.
