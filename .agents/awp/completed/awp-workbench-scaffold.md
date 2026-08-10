# AWP: AI Video Director's Workbench Platform - Initial Scaffold

- **Scope:**
  - `frontend/src/store/useWorkbenchStore.ts`
  - `frontend/src/App.tsx` (or Next.js equivalent)
  - `frontend/src/components/workspace/MediaReferencePlayer.tsx`
  - `frontend/src/components/workspace/NarrativeBlueprint.tsx`
  - `frontend/src/components/workspace/ScriptInspector.tsx`
- **Goal:** Set up the Zustand state store (`useWorkbenchStore`) and build the 3-pane layout shell using Tailwind CSS.
- **Acceptance Criteria:**
  - Zustand store correctly manages `ActionBlock` states and video properties.
  - The UI has a reactive 3-pane split (Media Player, Narrative Blueprint, Script Inspector).
  - The framework mismatch (Vite vs Next.js) is resolved.
