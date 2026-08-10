# ADR: Transition to Human-in-the-Loop Workbench

## Status
Proposed

## Context
Currently, the project functions as an automated "short only generator" that suffers from the "garbage in, garbage out" problem. Relying entirely on AI (Vision-LLMs or tools) to analyze raw footage without context leads to hallucinations and low-quality output. The user experience does not allow for precise directorial control.

## Decision
We are pivoting the core architecture from a "Fully Automated Shorts Generator" to a "Highly Supportive Human Viewer Setup" (AI Director's Workbench).
- We will build a platform that makes it extremely easy for users to input precise details, context, and action plans on a second-by-second basis for their uploaded video.
- The platform will collect deep user intent, style, and directorial notes via a 3-pane UI (Media Player, Narrative Blueprint with Action Blocks, and Script Inspector).
- We will stick to the existing **Vite + React SPA** setup rather than migrating to Next.js, saving refactoring time while still delivering the required reactive UI.
- The AI's role will shift to handling narration (TTS), script generation, and video editing/rendering (FFmpeg/MoviePy) *strictly based on the user's structured blueprint*.

## Consequences
- **Positive:** Massive increase in video quality and narrative coherence. Eliminates AI hallucinations regarding on-screen events.
- **Positive:** Gives content creators fine-grained control over the final product.
- **Negative/Risk:** Requires building a complex, highly reactive frontend capable of precise video synchronization, hotkeys, and state management (Zustand).
- **Negative/Risk:** The backend API will need to be refactored to accept structured JSON blueprints rather than generating them from scratch.
