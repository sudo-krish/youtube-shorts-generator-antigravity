---
domain: Frontend
folder_path: docs/Frontend
description: Frontend setup, components, UI guidelines, and React details.
veracity_score: 4
tags:
  - frontend
  - ui
  - react
---

# Antigravity Studio - Frontend Workspace

A state-of-the-art, hyper-premium React (Vite + TailwindCSS) workspace built to monitor and control the Antigravity Shorts Engine.

## Features
- **Aurora Dark Mode UI**: A highly aesthetic, deep-space interface utilizing slow-moving CSS radial blur gradients (cyan, magenta, violet) combined with `backdrop-blur-2xl` glass panels.
- **3-Phase Workflow Wizard**: A logical progression flow:
  1. **Upload Dropzone**: A massive, animated drag-and-drop region for raw VODs.
  2. **Configuration Panel**: Interactive selection cards for game metadata and vibe tuning.
  3. **Live Execution View**: An AWS Step Functions-style node graph representing the backend AI assembly line, featuring live polling and auto-fetched exception logs on failure.
- **Modular Architecture**: Clean, single-responsibility components (`Sidebar`, `UploadDropzone`, `ConfigurationPanel`, `ExecutionView`, `LogViewer`, `DatabaseViewer`).
- **Live Terminal (LogViewer)**: An embedded WebSocket-powered terminal inside the `ExecutionView` that receives raw, filtered AI reasoning logs straight from the backend in real-time.
- **Database Inspector**: A full-page raw SQLite table viewer (`/api/db/dump`) to visualize VOD configurations, session states, and job execution stages. Features a global "Wipe" button to nuke backend runs.
- **Real-Time Token Tracker**: Subscribes to the backend's `/api/analyze` payload to render an animated metric dashboard of the Antigravity SDK's Prompt, Completion, and Total tokens.
- **Advanced Engine Toggles**: A suite of premium switches for future capabilities like Intelligent B-Roll injection, Audio-Driven Zooms, and Multi-Platform SEO.

## Quickstart
1. Install dependencies:
   ```bash
   cd frontend
   npm install
   ```

2. Start the dev server:
   ```bash
   npm run dev
   ```

3. Open `http://localhost:5173`. Make sure the FastAPI backend is running on `port 8000` to handle video uploads!
