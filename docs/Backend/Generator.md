---
domain: Backend
folder_path: docs/Backend
description: "Slicing logic that converts AI JSON blueprints into physical MP4 chunks."
veracity_score: 5
tags:
  - generator
  - slicing
  - file_manager
---

# Slicing & File Management

## Overview
The `generator` module acts as the bridge between the AI's abstract JSON blueprint and the physical FFmpeg Engine. It is responsible for organizing the project directory and slicing the master VOD into raw chunks based on the AI's timestamp data.

## `file_manager.py`
A simple utility script that creates isolated project directories for every processed video.
- **Directory Structure**: Creates `outputs/{video_id}/`.
- All sliced `.mp4` chunks and their associated metadata `.json` files are dumped into this specific folder to prevent file-name collisions when multiple users or jobs are running concurrently.

## `cutter.py`
The primary slicing logic. When `POST /api/splice` or the internal pipeline is triggered, `generate_files_from_json` is called.

### 1. Parsing the Blueprint
It loops over the `shorts` array in the JSON blueprint. For each variant, it iterates over the dynamic array of `phases`.

### 2. Physical Slicing
For each phase, it calls `_prep_clip`:
- Extracts `start_time` and `end_time` to calculate `duration`.
- Runs a fast FFmpeg pass (`-c:v libx264 -preset ultrafast`) to cut that specific phase from the original video.
- The output file is formatted predictably: `outputs/{video_id}/{video_id}_{variant_id}_{phase_index}_{phase_id}.mp4`.

### 3. Metadata Extraction
Crucially, FFmpeg only cares about video and audio streams. The Generator must extract the AI's complex metadata (like `start_focus_x` tracking coordinates, text overlays, and high-retention visual punch-ins) and save them alongside the video chunk.
- It writes a matching `.json` file for every `.mp4` chunk (e.g., `..._phase_1.json`).
- This JSON sidecar is what the FFmpeg `engine.py` reads during Stage 1 chunk processing to know exactly how to crop and apply effects to that specific slice.

### 4. Payload Construction
Finally, it bundles all generated file paths and the Director's chosen `background_audio_track` into a `clips_data` dictionary and returns it so `main.py` can pass it off to the Pipeline Editor.
