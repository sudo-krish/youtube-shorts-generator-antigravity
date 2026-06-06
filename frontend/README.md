# Antigravity Studio - Frontend Workspace

A state-of-the-art, hyper-premium React (Vite + TailwindCSS) workspace built to monitor and control the Antigravity Shorts Engine.

## Features
- **Cinematic Monochromatic UI**: A high-end frosted glassmorphism interface (`backdrop-blur-3xl`, low-opacity borders) designed to look like executive software.
- **Interactive Timeline Workspace**: A draggable range-slider UI that visualizes the AI's "Proposition -> Struggle -> Result" timestamps, allowing creators to perfectly adjust the cuts before the final render.
- **Real-Time Token Tracker**: Subscribes to the backend's `/api/upload` payload to render an animated metric dashboard of the Antigravity SDK's Prompt, Completion, and Total tokens.
- **Advanced Engine Toggles**: A suite of premium switches for future capabilities like Intelligent B-Roll injection, Audio-Driven Zooms, and Multi-Platform SEO.
- **Physics-Based Animation**: Uses `animejs` for smooth spring entrances, levitating widgets, and staggering nodes.

## Quickstart
1. Install dependencies:
   ```bash
   cd frontend
   npm install
   ```

2. Start the dev server:
   ```bash
   npm run dev
   ```

3. Open `http://localhost:5173`. Make sure the FastAPI backend is running on `port 8000` to handle video uploads!
