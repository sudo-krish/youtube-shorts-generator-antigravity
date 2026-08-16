# User Flow & Implementation Plan

This document details the exact user flow across the platform. The system is designed sequentially, ensuring the user has granular control over script, mapping, audio generation, and final visual edits.

---

## Part 1: Project Setup & Script Generation (Page 1)
**The User Experience:**
- **Login & Project Creation:** The user logs in, clicks "Create Project," and selects the format: **Long Format** or **Short Format**.
- **Project Metadata:** The user defines the project context:
  - **Game Name:** (e.g., Black Myth: Wukong, Valorant)
  - **Game Genre:** (e.g., Story Mode, FPS, RPG)
  - **Overall Theme:** (e.g., Lore explanation, gameplay rant)
- **AI-Assisted Scripting (Context Aware):**
  - The script editor utilizes the metadata to suggest highly contextual prompts.
  - *Example:* If Wukong, it suggests: *"Write a detailed historical and dramatic story on the myth of the Pagoda Realm."*
- **Script Finalization & Pre-Processing:** Once the user finalizes the script, it is broken down into distinct paragraphs. A backend pass estimates the speech duration metadata for each paragraph to assist with mapping.

---

## Part 2: Video and Script Syncing (Page 2 - The Mapping UI)
**The User Experience:**
- **The Interface:** The user sees their broken-down script paragraphs alongside the **Audio Duration Metadata** (e.g., *Paragraph 1: 5.2 seconds of speech*).
- **The Mapping Action:**
  1. The user clicks on a paragraph.
  2. They scrub their uploaded video and set **IN** and **OUT** pointers on the timeline.
- **The Remark Box:** Immediately upon placing the pointers, a details box pops up.
  - The user adds practical **voice manipulation directives** (e.g., *"be sad here"*, *"slow down and be dramatic"*).
  - The user adds practical **event flags** (e.g., *"add a death flag at the end"*).
- **The Duration Warning System:**
  - If the user selects **10 seconds** of video for a paragraph estimated at **5.2 seconds** of speech, a warning triggers: *"Video length exceeds audio length. How do you want to handle this?"*
  - The user chooses a resolution (e.g., *"Speed up video"*, *"Trim video"*).

---

## Part 3: Audio Generation & Tweaking (Page 3)
**The User Experience:**
- **Voice Selection & Sampling:** The user moves to Page 3. Here, they select their desired voice model and can sample the voices before committing.
- **Applying Directives:** 
  - The system sends the text paragraphs to the audio generator, injecting the **voice manipulations** from the Page 2 Remark Box (e.g., *"be sad"*) directly into the generation prompt.
  - The data sent to the audio generator is fully exposed and tweakable. 
- **Iterative Generation:** 
  - The user generates the audio per paragraph.
  - If they do not like the tone (e.g., it sounds too robotic), they can manually tweak the prompt (e.g., *"Use a natural tone"*) and regenerate that specific audio chunk until satisfied.
  - The final, absolute audio track lengths are locked.

---

## Part 4: Video Editing Style Engine (Page 4 - The Preview & Edit Stage)
This phase is purely programmatic. **There is no AI used here.** It is a strict execution engine that relies entirely on the enriched metadata passed down from the previous steps.

**The User Experience:**
- **Paragraph-by-Paragraph Workflow:** The UI does not show one massive timeline. Instead, every paragraph is treated as a separate, isolated mini-clip.
- **Generating the Clip:** The user clicks "Generate" on a single paragraph. The backend engine resolves the inputs:
  - It takes the finalized audio chunk.
  - It takes the raw video (IN/OUT points).
  - It applies the resolution from the Duration Warning (e.g., executing a programmatic FFmpeg speed ramp to fit the 10s video into 5.2s).
  - It applies the event flags (e.g., programmatically overlaying a grayscale "Wasted" effect at the exact end timestamp).
- **Editable Edits:** 
  - The user previews the generated mini-clip.
  - Because they now have both the video and audio perfectly synced in front of them, **the edits are fully editable.** 
  - If they don't like the speed ramp or the death flag, they can remove it, change it, or add new visual edits directly on this page, and regenerate the preview for that paragraph.

---

## Part 5: Final Export (The End Project)
**The User Experience:**
- Once the user is completely satisfied with all the individual, paragraph-sized clips on Page 4, they proceed to the final page.
- **Project Stitching:** The backend rendering engine concatenates all the individual, perfectly synced clips together.
- **Final Output:** Subtitles are overlaid (if applicable), and the final MP4 is rendered and provided to the user for download or direct upload.
