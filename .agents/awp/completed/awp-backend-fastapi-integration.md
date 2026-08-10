# AWP: FastAPI Backend Integration (Vision LLM & FFmpeg)

- **Scope:**
  - `backend/modules/vision/analyze_frame.py` (New)
  - `backend/modules/video/batch_crop.py` (New)
  - `frontend/src/components/workspace/MediaReferencePlayer.tsx`
  - `frontend/src/components/workspace/ClipLibrary.tsx`
- **Goal:** Build the backend endpoints for Vision LLM frame analysis and FFmpeg cropping, and wire them up to the frontend UI.
- **Acceptance Criteria:**
  - The `analyze-frame` endpoint accepts a base64 image and returns Gemini 1.5 Pro transcription/suggestions.
  - The `batch-crop` endpoint accepts timestamps and generates new trimmed MP4 files using FFmpeg.
  - Dropping a marker (`M`) in the frontend automatically calls the backend and displays real AI context.
  - Clicking "Batch Process Clips" triggers the FFmpeg pipeline.
