# AWP: Enhanced Video Controls and Frame Extraction

- **Scope:**
  - `frontend/src/store/useWorkbenchStore.ts`
  - `frontend/src/components/workspace/MediaReferencePlayer.tsx`
  - `frontend/src/App.tsx` (Hotkey Logic)
- **Goal:** Build the custom Scrubber, Speed Controls, and HTML5 Canvas Frame Extraction in the Media Player.
- **Acceptance Criteria:**
  - The Media Player has a working scrubber and speed multiplier dropdown.
  - Hitting `M` captures a base64 frame image of the video at that timestamp.
  - The base64 frame is saved into the newly generated Action Block.
