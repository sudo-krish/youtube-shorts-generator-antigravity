# Core Objective: Audio-Driven Video Editor

## Vision Overview
We are building a highly automated, audio-driven programmatic video editing platform designed for generating both **long-format and short-format content**. This will be a versatile tool with multiple features. 

The core philosophy of this platform is that **video editing is slaved to audio timing**. 

The user does not deal with complex traditional video timelines. Instead, they map text to source video clips, and the backend handles the exact mathematical synchronization and rendering. The existing platform will be torn down to its bare bones and rebuilt around this core philosophy.

---

## 1. The Script & Mapping UI
The user interface is a streamlined, split-screen text-to-video mapping tool.

*   **Left Side (The Script):** The user writes their story or imports an AI-generated draft text.
*   **Right Side (The Video Bank):** The user uploads their raw gameplay or B-roll files.
*   **The Action:** The user highlights a sentence in the script (e.g., *"His spear moves faster than my eye can track"*), clicks a clip from the Video Bank, and drags a slider to assign a timestamp segment: *"Use timestamps 04:12 - 04:18 for this line."*

## 2. The Audio Engine (The Pace Setter)
This is the most critical backend step. The audio entirely dictates the pacing and duration of the final video segments.

*   When the user hits "Build Video," the backend sends the text script to a high-tier TTS API (e.g., ElevenLabs).
*   The API returns the generated audio files alongside the exact duration of each spoken line.
*   *Example:* The backend calculates that Line 1 takes exactly **4.2 seconds** to speak.

## 3. The Synchronization Engine (The Magic)
This is where the programmatic logic resolves the gap between user-selected video durations and the actual TTS audio durations.

If a user assigns a **6.0-second** video clip to a line of text, but the TTS audio for that line is only **4.2 seconds** long, the programmatic editor automatically resolves this using one of the following dynamic methods:
*   **Trim:** It trims the video down from 6.0s to 4.2s to match the audio perfectly.
*   **Time-Stretch:** It slightly slows down the 4.2s video to stretch it to 6.0s for a cinematic, slow-motion effect.
*   **Freeze-Frame:** It plays the video at normal speed, freezing on the final frame while the audio finishes speaking.

*The user never touches a video timeline—the code calculates the math and synchronizes everything.*

## 4. The Render Engine
The platform compiles all assets and renders the final video programmatically.

*   It aggregates the TTS audio chunks, the dynamically trimmed/stretched video clips, and the generated subtitle files.
*   It passes everything to a programmatic rendering engine.
*   **Implementation Options:**
    *   **Remotion (React/Node.js):** Highly recommended. Build the video programmatically using React components and auto-render via FFmpeg under the hood.
    *   **MoviePy / FFmpeg (Python):** The classic, raw programmatic video editing stack.
