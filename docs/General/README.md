---
domain: "General"
folder_path: "docs/General"
description: "High-level overview of the Antigravity Shorts Engine, setup instructions, and core workflows."
veracity_score: 5
tags:
  - overview
  - setup
  - quickstart
  - architecture
---

# Antigravity Shorts Engine Flow

An autonomous, multi-agent AI pipeline that takes massive raw gaming VODs and intelligently edits them into highly engaging, retention-optimized YouTube Shorts.

## Overview
Unlike standard clipping tools that just chop videos based on arbitrary timestamps, Antigravity Shorts Engine runs a full **Director's Room Pipeline**. It uses a sequential cascade of AI Agents to watch the video, understand the cultural meta, generate a narrative script, and physically edit the video using cinematic FFmpeg filters and XFade transitions.

## 1. Pre-Generated Context Engine
The AI does not blindly hallucinate. We run pre-processing Python tools before the LLM is ever invoked.
- **Audio Spikes:** Locates high-decibel moments (screams, gunshots) using `scipy`.
- **OCR Kills:** Reads the killfeed via `pytesseract` to provide hard evidence.
- **YOLOv8 Tracking:** Tracks player movement dynamically for hyper-panning.

## 2. The 6-Agent AI Assembly Line
A rigid prompt chain designed to drastically reduce hallucinations and enforce formatting.
- **Observer:** Extracts dense visual data logs.
- **Scriptwriter:** Generates narrative templates (Meme Fail, Clutch).
- **Director:** Injects pacing, background music (semantic matching), and text overlays.
- **Editor:** Translates creative vibes into physical FFmpeg parameters.
- **YouTube Specialist:** Validates algorithmic pacing and fixes temporal math.
- **Builder:** Outputs the strict Pydantic JSON structure.

## 3. FFmpeg Dynamic Rendering
- Uses a multi-stage chunk rendering strategy to avoid memory overflow.
- Employs `xfade` for cinematic transitions (wipes, zooms) instead of jarring hard cuts.
- Applies dynamic ducking via sidechain compression to automatically lower music volume when the player speaks.

## How to Run Locally

### Backend (FastAPI)
```bash
cd backend
uv sync
uv run uvicorn main:app --reload --port 8000
```
*(Requires `GEMINI_API_KEY` in environment)*

### Frontend (React + Vite)
```bash
cd frontend
npm install
npm run dev
```
*(Runs on `http://localhost:5173`)*
