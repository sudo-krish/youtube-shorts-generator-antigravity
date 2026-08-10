# AWP: Action Block AI Context UI

- **Scope:**
  - `frontend/src/store/useWorkbenchStore.ts`
  - `frontend/src/components/workspace/MediaReferencePlayer.tsx`
  - `frontend/src/components/workspace/NarrativeBlueprint.tsx`
- **Goal:** Update the Action Block UI to display the AI's transcription (`aiContext`) and clickable narrative suggestion pills.
- **Acceptance Criteria:**
  - A block displays the AI Context visually (e.g., as a transcription quote).
  - A block displays 3 dummy narrative suggestions.
  - Clicking a suggestion populates the `directorNotes` for that block.
