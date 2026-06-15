---
domain: Backend
folder_path: docs/Backend
description: "FFmpeg editing capabilities registry, visual effects, temporal effects, and hyperframe math."
veracity_score: 5
tags:
  - capabilities
  - effects
  - hyperframe
  - registry
---

# Capabilities Registry

## Overview
The capabilities system (`backend/pipeline/capabilities/`) is a highly modular architecture that defines exactly what the Antigravity engine is physically capable of executing via FFmpeg.

By isolating FFmpeg filter math into OOP classes, we avoid hardcoding filter strings. This also allows the backend to generate a dynamic "Capabilities Menu" (`registry.py`) which is injected into the Editor Agent's prompt. The AI literally reads what functions exist and calls them by name.

## Directory Structure

### `effects/`
Contains Python classes inheriting from `BaseEffect`.
- `visual.py`: Classes like `VHS_Overlay`, `Deepfried`, `Motion_Blur`, `Dynamic_Glow`. These return specific FFmpeg video filters (`-vf` strings).
- `temporal.py`: Classes like `Slow_Motion` and `Time_Warp`. These return paired video and audio filters (e.g. `setpts`, `atempo`) to ensure audio desync doesn't happen.
- `audio.py`: Classes like `Bass_Boost` and `Muffled_Audio`.
- `registry.py`: Scans all classes and constructs a JSON menu of effect names, parameters, and descriptions for the Editor Agent.

### `audio/`
- `mixing.py`: The heart of the audio engine. Handles dynamic semantic audio selection, impact SFX layering via `adelay`, and sidechain compression ducking. 

### `transformations/`
- `hyperframe.py`: Contains complex math utilities for spatial crop panning. Translates the YOLOv8 coordinate `[start_x, end_x]` data into dynamic FFmpeg `crop='x_expr'` polynomials so the camera smoothly tracks the player across the screen.

### `text/`
- `overlays.py`: Handles typography data extraction. It invokes the WhisperX ASR engine to get highly accurate word-level timings and dumps them into `captions.json`.
- `compositor/index.js`: A dedicated Node.js microservice. It uses Puppeteer to launch an off-screen Chromium browser, reads `captions.json`, and renders dynamic HTML5 "Hormozi Pop" animations on an HTML Canvas. It captures the canvas frame-by-frame and uses FFmpeg to output a transparent `.webm` video for the Python engine to overlay.
