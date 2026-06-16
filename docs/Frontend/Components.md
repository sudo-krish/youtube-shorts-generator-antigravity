---
domain: Frontend
folder_path: docs/Frontend
description: "Core UI components including ExecutionView, PipelineVisualizer, and LogViewer."
veracity_score: 5
tags:
  - components
  - ui
  - visualizer
  - logs
---

# Core UI Components

## Execution & Monitoring

### `ExecutionView.tsx` & `RenderView.tsx`
The control centers while a job is running or queued for rendering.
- **Polling Loop**: Runs a `setInterval` every 3 seconds to fetch the `agent_states` dictionary from the backend.
- **Redrive UI**: If the status returns `failed`, it exposes a "Redrive" button to trigger `POST /api/redrive/{job_id}`.
- **Split Pane**: Renders the `PipelineVisualizer` at the top. The bottom is split between a "Node Inspection" JSON preview panel and the `LogViewer`.
- **Render UI (`RenderView.tsx`)**: Allows batch queuing of generated short blueprints to FFmpeg. Recently updated to support an individual **"Render Video"** / **"Retry Render"** action per variant via isolated hovering.

### `Dashboard.tsx`
A dedicated cost tracking and analytics view.
- Connects to `/api/metrics/usage` and `/api/metrics/balance` (direct HTTP to DeepSeek).
- Visualizes real-time token spend, provider API balances, and rate limit occurrences across models.

### `PipelineVisualizer.tsx`
A complex, custom-built node graph using standard DOM elements (flexbox/relative positioning) rather than a heavy canvas library.
- Maps the dynamic `agent_states` dictionary into visual nodes.
- **Parallel Chunk Handling**: Dynamically groups states that start with `chunk_{id}_` into vertical swimlanes. This allows the user to see, for example, 3 parallel chunks running the `Observer` -> `Director` pipeline simultaneously.
- **Interactivity**: Clicking a node triggers `handleNodeClick` in `ExecutionView`, which fetches `GET /api/jobs/{job_id}/nodes/{node_id}` to display the raw text/JSON output of that specific agent in the preview pane.

### `LogViewer.tsx`
A terminal emulator component.
- Connects to `ws://localhost:8000/api/jobs/{job_id}/logs/stream`.
- Automatically auto-scrolls to the bottom as new logs stream in from the Python `logging` module.

## Configuration & Setup

### `UploadDropzone.tsx`
A drag-and-drop file uploader with smooth hover states and upload progress simulation. Restricts inputs to `.mp4` files.

### `ConfigurationPanel.tsx`
A form to capture the global UI metadata.
- Inputs: `Game Name` (e.g., Valorant, Apex Legends), `Region` (for web trends), and `Player Vibe` (e.g., Toxic, Chill, Sweaty).
- Includes the `ModelSettings` component, which allows the user to override the global LLM model mapping (e.g., swapping `deepseek-v4-flash` for `deepseek-v4-pro` on specific agents) before hitting "Start".

### `DatabaseViewer.tsx`
A debug utility accessible from the Sidebar.
- Fetches `GET /api/db/dump` to render raw tables for `videos`, `jobs`, and `job_stages`.
- Includes a "Nuke Database" button that calls `DELETE /api/db/clear` to securely reset the backend workspace.
