---
domain: Backend
folder_path: docs/Backend
description: Qwen2.5-VL Video Game Analysis Strategy and Roadmap
veracity_score: 5
tags:
  - todo
  - roadmap
  - backend
  - qwen
  - computer-vision
---

# 🚀 Next-Gen Video Game Analysis Roadmap (Qwen2.5-VL Pipeline)

## Core Philosophy
Standard 1 FPS sampling completely fails for fast-paced video games. By the time a model sees the next frame, crucial events—like rapid camera movements, enemy spawns, damage indicators, UI changes, and text tickers (kill feeds, chat logs)—have already vanished, leading to severe hallucination and context loss. 

To bypass this, we are pivoting to a **Hyper-Dense Micro-Chunking Strategy** leveraging **Qwen2.5-VL**, utilizing its Native Dynamic Resolution, Dynamic FPS Sampling, and Absolute Time Encoding (M-RoPE).

---

## Phase 1: Dynamic "Event-Driven" FPS Sampler
Force the model to only spend its limited context tokens on action-heavy sequences.
- [ ] **Build Delta-Threshold Sampler**: Create a Python script (`OpenCV` / `scikit-image`) that computes pixel-change thresholds between frames.
- [ ] **Variable Frame Extraction**:
  - *Low Action (Menus, loading screens)*: Sample at 0.5 FPS (or skip entirely).
  - *High Action (Combat, rapid panning, gunfights)*: Dynamically ramp up to 15-30 FPS for that specific window.

## Phase 2: Token Constraints & Spatial Downsampling
A 0.5B / 1.5B model will crash or hallucinate if fed 60 frames of 1080p video. We trade spatial resolution for temporal resolution.
- [ ] **Spatial Downsampling Script**: Force FFmpeg to compress the spatial size of chunks to 360p or 480p. Qwen's robust OCR can still read health numbers and kill feeds at this resolution.
- [ ] **Implement Qwen Token Constraints**:
  - Integrate `qwen-vl-utils`.
  - Pass the dense FPS (e.g., `fps: 10.0` or `30.0`).
  - Hardcap the resolution with `max_pixels: 360 * 360`.

## Phase 3: The Micro-Chunk Sliding Window Pipeline
Instead of feeding an entire 60-second video at a low framerate, we feed 2-second bursts at 30 FPS. To the 0.5B model, it's the exact same token math (60 total frames), but with perfect micro-second temporal resolution.
- [ ] **Implement Sliding Window Cutter**: Use FFmpeg to slice gameplay into overlapping 1-to-3 second micro-chunks.
- [ ] **Configure 50% Overlap**: Ensure chunks overlap (e.g., Chunk 1 is 0s–2s, Chunk 2 is 1s–3s) so fast actions at the boundary aren't missed.
- [ ] **Micro-Prompt Engineering**: Standardize prompts sent with micro-chunks (e.g., *"What event occurred in these 2 seconds? Track health bars, kill feeds, and ultimate status changes."*).

## Phase 4: State Tracking / Global Memory Architecture (The "Macro" Context)
Chunking solves the micro-hallucination problem but causes the model to lose the "big picture" (why did the player just die?). We solve this with continuous memory injection.
- [ ] **Implement State Tracking Variable**: Create a global memory context string that holds the outcome of previous chunks.
- [ ] **Chunk Output Extraction**: Parse the model's text event output (e.g., *"Player took 50 damage from Genji"*).
- [ ] **Memory Prepending**: Inject the previous state into the system prompt for the next chunk pass.
  - *Example Prompt*: `"Previous State: Player has an empty rifle and took 50 damage. Now analyze these next 2 seconds."`
- [ ] **State Pruning**: Ensure the state tracking string doesn't grow infinitely; summarize or prune old state data if it exceeds token limits.
