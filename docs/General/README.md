---
domain: General
folder_path: docs/General
description: General project overview and setup instructions.
veracity_score: 5
tags: [overview, setup, quickstart, architecture]
---

# Antigravity Shorts Engine

An autonomous, multi-agent AI pipeline that takes massive raw gaming VODs and intelligently edits them into highly engaging, retention-optimized YouTube Shorts.

## Overview

Unlike standard clipping tools that just chop videos based on arbitrary timestamps, Antigravity Shorts Engine runs a full **Director's Room Pipeline**. It uses a sequential cascade of AI Agents to watch the video, understand the cultural meta, generate a narrative script, and physically edit the video using cinematic FFmpeg filters and XFade transitions.

## Key Features

- **Pre-Generated Context Engine**: The AI does not blindly hallucinate. We run pre-processing Python tools to mathematically locate audio decibel spikes (screams, gunshots), extract killfeed texts via OCR, and pull trending regional memes before the AI even starts analyzing.
- **The 6-Agent AI Assembly Line**: 
  - *Observer*: Extracts visual data using the audio spike map.
  - *Scriptwriter*: Uses live web-trends to formulate templates (e.g., Meme Fail, Clutch).
  - *Director*: Injects pacing, narrative text, and local SFX.
  - *Editor*: Translates vibes to physical FFmpeg editing capabilities.
  - *YouTube Specialist*: The Final Polish Editor. Actively fixes math errors, tweaks pacing, and optimizes hooks against algorithmic retention rules.
  - *Builder*: Formats the final validated plans into a precise JSON blueprint.
- **Dynamic N-Phase Engine**: No more rigid 3-part boundaries. A short can be a fast 2-part punchline or a massive 5-part clutch sequence.
- **XFade Pipeline & Cinematic Effects**: Stops using jarring hard cuts. Dynamically calculates temporal offsets to weave clips together using overlapping `xfade` transitions (wipes, zooms, blurs) and applies premium visual effects (`VHS`, `Motion_Blur`, `Deepfried`).
- **Animated ASS Subtitles**: Subtitles don't just appear—they dynamically *pop* and scale on-screen per word, matching highly engaging "Alex Hormozi" retention styles.

## How to Run Locally

This project is split into a Python/FastAPI backend and a React/Vite frontend. You need to run both concurrently in separate terminal windows.

### 1. Start the Backend (FastAPI / uv)
The backend uses `uv` as its package manager and requires FFmpeg to be installed on your system.
```bash
cd backend
uv sync
uv run uvicorn main:app --reload --port 8000
```
*Note: Make sure your `GEMINI_API_KEY` is exported in your environment.*

**Troubleshooting Port Errors:**
If you get an error saying `[Errno 98] Address already in use` when starting the backend, it means a previous session crashed or is still running in the background. You can forcefully kill it using:
```bash
fuser -k 8000/tcp
```

### 2. Start the Frontend (React + Vite)
Open a new terminal window for the frontend.
```bash
cd frontend
npm install
npm run dev
```
The frontend will start on `http://localhost:5173`. Open this URL in your browser to access the Antigravity Studio UI.

---

## Quickstart Guide

1. **Upload**: Open the React Frontend (`localhost:5173`) and upload a `.mp4` file. Define your specific UI metadata (`Game`, `Region`, `Vibe`).
2. **Analysis**: The FastAPI Backend processes the video using the 6-agent pipeline, generating multiple JSON blueprints for different narrative variations.
3. **Render**: The File Manager slices the phases and the Pipeline Editor stitches them perfectly together with effects and music. Final rendered `.mp4` shorts will appear in the `backend/outputs/` directory.
