# AWP: Video Upload UI & Flow

- **Scope:**
  - `frontend/src/store/useWorkbenchStore.ts`
  - `frontend/src/App.tsx`
  - `frontend/src/components/upload/WorkbenchUploadScreen.tsx` (New)
  - `frontend/src/components/workspace/MediaReferencePlayer.tsx`
- **Goal:** Implement the "Upload Video" entry screen and integrate an actual HTML5 video player into the Workbench.
- **Acceptance Criteria:**
  - App starts on a drag-and-drop upload screen if no video is loaded.
  - Selecting a local `.mp4` file transitions the UI to the 3-pane Workbench.
  - The `MediaReferencePlayer` plays the selected video using a local object URL.
  - The video's playback time automatically syncs with the Zustand store.
