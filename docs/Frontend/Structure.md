---
domain: Frontend
folder_path: docs/Frontend
description: "React architecture, App routing state machine, and Tailwind theming."
veracity_score: 5
tags:
  - react
  - vite
  - tailwind
  - state
---

# Frontend Architecture & Structure

## Overview
The Antigravity frontend is built with **React**, **Vite**, and **Tailwind CSS**. It is designed as a futuristic, dark-mode, high-performance UI specifically tailored to manage complex asynchronous AI workflows.

The entry point is `frontend/src/App.tsx`.

## State & Flow (`App.tsx`)
The `App` component acts as a state machine managing a `wizardState`. It routes the user through four primary states:

1. **`UPLOAD`**: Shows the `UploadDropzone`. The user drops an `.mp4` file, it uploads via the `/api/upload` endpoint, and saves the returning `videoId`.
2. **`CONFIG`**: Shows the `ConfigurationPanel`. The user defines global metadata (Game Name, Region, Vibe). Upon clicking "Start AI Assembly", it triggers `/api/analyze` and transitions to `ExecutionView`.
3. **`EXECUTION`** (`ExecutionView.tsx`): The main polling interface. It connects to the backend and polls `/api/jobs/{job_id}/status`. It renders the live `PipelineVisualizer` graph.
4. **`RENDER_VIEW`** (`RenderView.tsx`): Once the AI is done, the user can trigger the actual FFmpeg background processes to render the `_segments.json` variants.

## Styling & Theme
The UI uses a heavily customized **Tailwind CSS** configuration (`tailwind.config.js` and `index.css`).
- **Premium Dark Mode**: Backgrounds use colors like `premium-dark` (`#0a0a0a`), overlaid with `mix-blend-screen` aurora gradients (Cyan, Magenta, Violet).
- **Glassmorphism**: Extensive use of `backdrop-blur-xl`, semi-transparent borders (`border-white/10`), and soft inner shadows (`shadow-glass`) to create depth.
- **Animations**: Custom keyframes for `aurora-spin`, `blob`, and `shimmer` effects to make the interface feel alive even while waiting for long background tasks.

## API Integration
All backend communication is centralized in `frontend/src/api/index.ts`. 
- **REST Endpoints**: Wraps `fetch` calls for `/api/analyze`, `/api/jobs/{job_id}/redrive`, etc.
- **WebSocket Streaming**: Used by `LogViewer.tsx` to stream `job_id.log` tailing directly into a terminal-like UI component.
