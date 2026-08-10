# AWP: Video Cropping & Segmenting UI

- **Scope:**
  - `frontend/src/store/useWorkbenchStore.ts`
  - `frontend/src/components/workspace/MediaReferencePlayer.tsx`
  - `frontend/src/components/workspace/ClipLibrary.tsx` (New)
- **Goal:** Add In/Out point hotkeys and UI to allow the user to isolate and crop sections of the video, saving them into a Clip Library.
- **Acceptance Criteria:**
  - The store tracks `inPoint`, `outPoint`, and an array of `clips`.
  - The Media Player UI has buttons and hotkeys (`I`, `O`) to set the In and Out points on the timeline.
  - The user can "Save Clip" to add it to the Clip Library.
  - The Clip Library displays a list of saved clips with a "Batch Process" button.
