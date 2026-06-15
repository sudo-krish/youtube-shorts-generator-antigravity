---
domain: Backend
folder_path: docs/Backend
description: Backend services, APIs, and audio/video processing details.
veracity_score: 4
tags: [backend, api, python]
---

# Antigravity Studio - Autonomous Factory Engine

The powerhouse behind the Antigravity Shorts Engine. This FastAPI-driven backend has evolved into a fully **Autonomous Video Factory**. It programmatically slices, analyzes, and randomly assembles thousands of unique viral gaming shorts using a custom AI pipeline and the real `google-antigravity` SDK.

## The Architecture: Autonomous Clip Splicing
We have migrated away from a traditional "Interactive Timeline Editor". Instead, the engine operates as an autonomous factory:

1. **Multimodal AI Analysis (`google-antigravity`)**: When a `.mp4` is uploaded, it is fed natively into the Gemini 1.5 Pro model using the `google.antigravity` SDK `from_file()` hook. The model scans the *entire* video and returns a JSON list of every highlight.
2. **Categorization Buckets**: The AI categorizes every highlight into 3 distinct atomic buckets:
   - **Proposition**: The goal setup (e.g., "I need to beat this boss without taking damage").
   - **Struggle**: The low-health/failing chaos (e.g., multiple near-deaths, intense scrambling).
   - **Result**: The epic win or funny death.
3. **Background Splicer Worker (`splicer_worker.py`)**: A background worker uses `ffmpeg` to physically chop the master VOD into dozens of tiny `.mp4` clips and sorts them into `outputs/Proposition/`, `outputs/Struggle/`, and `outputs/Result/`.
4. **Random Assembly (`/api/generate-short`)**: The engine randomly selects one clip from each bucket, ensuring it has *never* assembled that specific combination before (via hash tracking). 
5. **Hyperframe & The Pop**: The assembled 3-part short is run through our custom OpenCV Action Tracker to enforce a perfect 9:16 vertical crop, and `whisperx` burns dynamic word-level captions into the final render!

## Setup & Quickstart (Powered by `uv`)

1. **Environment Variables (CRITICAL)**:
   We use the real `google-antigravity` SDK, which requires an API key. 
   Copy the template and add your key:
   ```bash
   cd backend
   cp .env.template .env
   # Open .env and set GEMINI_API_KEY
   ```

2. **Install dependencies**:
   We manage our Python environment with blazing fast [uv](https://github.com/astral-sh/uv).
   ```bash
   uv venv
   source .venv/bin/activate
   uv pip install -r requirements.txt
   uv add google-antigravity python-dotenv
   ```

3. **System Requirements**:
   Make sure you have FFmpeg installed on your system!
   ```bash
   # Ubuntu/Debian
   sudo apt install ffmpeg
   
   # MacOS
   brew install ffmpeg
   ```

4. **Start the Server**:
   ```bash
   uv run uvicorn main:app --port 8000 --reload
   ```

## Workflow
1. Upload a gaming video in the React frontend.
2. The AI will scan it and the Splicer Worker will begin filling your buckets.
3. Once clips appear in the Factory Dashboard, hit **Forge Random Viral Short** to generate your final output!
