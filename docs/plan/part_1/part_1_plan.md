# Part 1: Project Setup & Script Generation (Page 1)

## High-Level Flow (What We Want)
The primary goal of this phase is to onboard the user, gather project-specific context, and leverage our existing AI framework to help them write a structured, highly relevant script. This script is then broken down and prepared for mapping.

1. **Project Initiation**: User navigates to the dashboard and selects "Create New Project". They choose between **Long Format** (16:9) and **Short Format** (9:16).
2. **Metadata Intake**: The UI presents a form to gather crucial context:
   - **Game Name**: (e.g., "Valorant", "Black Myth: Wukong")
   - **Game Genre**: Dropdown (e.g., "FPS", "Story Mode", "RPG", "Strategy")
   - **Overall Theme**: (e.g., "Lore explanation", "Gameplay rant", "Tutorial", "Funny Moments")
3. **Context-Aware AI Scripting (Powered by DeepSeek)**:
   - The UI transitions to the **Script Editor**.
   - An AI Assistant panel sits beside the editor. Based on the collected metadata, the AI provides dynamic, clickable prompt suggestions.
   - *Example (Story Mode)*: "Tell me a dramatic myth about the Pagoda Realm."
   - *Example (FPS)*: "Write an aggressive rant about matchmaking in Bronze."
   - The user can click a suggestion, tweak it, and generate a draft. The draft populates the text editor using our existing DeepSeek integrations.
4. **Manual Editing**: The user is free to edit, rewrite, or delete any part of the AI-generated text.
5. **Script Finalization & Block Splitting**:
   - The user clicks **"Finalize Script"**.
   - The system automatically breaks the script down into **Paragraph Blocks** (typically 1-3 sentences).
6. **Pre-Processing (Audio Estimation)**:
   - The system uses an internal heuristic model to estimate the speech duration for each block.
   - This prepares the metadata needed for Page 2 (The Mapping UI). The user is then automatically routed to Page 2.

---

## Low-Level Design (How We Build It)
This section outlines the technological architecture, API contracts, and data structures required to support the high-level flow, explicitly leveraging the existing Python backend capabilities.

### 1. Technology Stack
- **Frontend**: React (Next.js/Vite), Tailwind CSS, Zustand/React Context.
- **Backend Core**: Python (FastAPI), extending the existing architecture in `backend/main.py`.
- **AI Framework (Existing)**: Leverage `backend/modules/ai/agents/llm/llm_client.py` specifically configured for **DeepSeek (`deepseek-v4-flash`)**. We will extend the existing `BaseDynamicAgent` pattern (like the current `ScriptWriterAgent`) to handle these new generation tasks.
- **Database**: SQLite (using the existing `antigravity.db` setup).

### 2. Core API Endpoints
- `POST /api/v1/projects`
  - **Payload**: `{ format, game_name, genre, theme }`
  - **Action**: Creates a new project in the DB and returns the `project_id`.
- `POST /api/v1/ai/suggest-prompts`
  - **Payload**: `{ game_name, genre, theme }`
  - **Action**: Invokes a lightweight DeepSeek prompt generator to return 3 highly contextual starting prompts based on the metadata.
- `POST /api/v1/ai/generate-script`
  - **Payload**: `{ prompt, game_name, genre, theme }`
  - **Action**: Invokes an extended version of `ScriptWriterAgent` to generate the script content based on the user's prompt and metadata.
- `POST /api/v1/script/finalize`
  - **Payload**: `{ project_id, full_text }`
  - **Action**: 
    1. Splits `full_text` by paragraph breaks (`\n\n`).
    2. Runs a fast heuristic estimation function: `duration_ms = (word_count / avg_words_per_sec) * 1000`.
    3. Saves blocks to DB.
    4. Returns array of formatted `ScriptBlock` objects.

### 3. Data Schema Definitions

**Project Model**
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "format": "LONG" | "SHORT",
  "metadata": {
    "game_name": "string",
    "genre": "string",
    "theme": "string"
  },
  "created_at": "timestamp",
  "status": "DRAFT" | "MAPPED" | "AUDIO_GENERATED" | "COMPLETED"
}
```

**ScriptBlock Model**
```json
{
  "id": "uuid",
  "project_id": "uuid",
  "block_index": "integer (0, 1, 2...)",
  "text_content": "string (the actual paragraph)",
  "estimated_duration_ms": "integer (e.g., 5200 for 5.2s)",
  "status": "PENDING"
}
```

### 4. Implementation Steps
1. **Scaffold Frontend Route**: Create `/projects/new` view containing the metadata intake form.
2. **Refactor AI Agents**: Extend the existing `ScriptWriterAgent` in `backend/modules/ai/agents/roles/scriptwriter.py` (or create a new `IdeationAgent`) to handle contextual prompt suggestions and draft generation via the existing `DeepSeekClient`.
3. **Build Script Editor UI**: Implement a rich text editor that handles the AI response gracefully.
4. **Implement Block Splitting Logic**: Write the parser that accurately splits the final text into manageable blocks.
5. **Implement Duration Estimator**: Write the lightweight heuristic function for Page 2 metadata.
6. **State Persistence**: Ensure the `ScriptBlock` array is saved to the global state and persisted to `antigravity.db` before routing to `/projects/[id]/mapping`.
