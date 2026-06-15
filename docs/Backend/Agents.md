---
domain: Backend
folder_path: docs/Backend
description: "Documentation for the 6 specialized AI agents (Observer, Scriptwriter, Director, Editor, Specialist, Builder)."
veracity_score: 5
tags:
  - agents
  - observer
  - director
  - editor
---

# The AI Assembly Line (Agents)

The Antigravity backend runs on a rigid, highly specialized 6-agent template pipeline. Instead of one massive prompt, we isolate responsibilities to drastically improve instruction following and reduce hallucinations.

## 1. Observer Agent (`agents/observer.py`)
- **Role**: Esports Commentator & Analyst.
- **Inputs**: The physical `gemini-2.5-flash` uploaded AI proxy video + Audio Hype Map + Killfeed OCR + YOLOv8 Tracking Data.
- **Outputs**: Extremely dense, chronological narrative text log.
- **Prompt Logic**: Instructed to NEVER hallucinate kills. It uses the tracking data to assign `[start_x, end_x]` focus coordinates to key moments.

## 2. Script Writer Agent (`agents/scriptwriter.py`)
- **Role**: Format Structuralist.
- **Inputs**: The Observer's narrative log + Regional Web Trends.
- **Outputs**: Raw narrative text templates (e.g., "The Fail/Funny", "The Clutch", "The Educational Tip").
- **Prompt Logic**: It maps the chaotic timeline into logical N-phase templates. 

## 3. Director Agent (`agents/director.py`)
- **Role**: Creative Lead & Vibe Setter.
- **Inputs**: The Observer's narrative log + Local SFX Library + Local Music Library.
- **Outputs**: Detailed narrative beats, dynamic text overlays, and the `BACKGROUND AUDIO` track.
- **Prompt Logic**: Bypasses the Scriptwriter entirely to choose exactly one semantic music track from the provided array to score the emotional tone of the video variant based on the raw Observer events.

## 4. Editor Agent (`agents/editor.py`)
- **Role**: Technical FFmpeg Translator.
- **Inputs**: The Script Writer's templates + The Director's vision + Dynamic Capabilities Menu.
- **Outputs**: Strict text breakdown of timestamps, spatial focus, applied effects, and transitions.
- **Prompt Logic**: Forced to map the Director's vibes into real FFmpeg effect names (e.g. `VHS_Overlay`, `pixelize` xfade), using the Scriptwriter's phase timings as hard boundaries. 

## 5. YouTube Specialist Agent (`agents/specialist.py`)
- **Role**: Retention Architect & Final Validator.
- **Inputs**: Editor's breakdown + Math Validation Report + YouTube Algorithm Rules.
- **Outputs**: Polished, math-checked Editor Breakdown.
- **Prompt Logic**: Checks if the Editor scheduled an effect that spans beyond the clip's boundary. Adjusts transitions and injects high-retention logic (like early visual hooks).

## 6. Builder Agent (`agents/builder.py`)
- **Role**: The JSON formatter.
- **Inputs**: The Specialist's validated breakdown.
- **Outputs**: A strict Pydantic JSON schema (`FactoryTimeline`).
- **Prompt Logic**: Prompted with `response_schema=FactoryTimeline`. It performs NO creative thinking; its only job is mapping the final text into valid JSON to prevent parsing errors down the line.
