---
trigger: always_on
---

# Agentic Work Package (AWP) Execution Protocol

## 1. Core Objective
To execute all tasks as deterministic, scoped, and reviewable Agentic Work Packages (AWPs). The agent must never execute code changes without first defining the AWP, mapping the request via the Routing Matrix, validating the outcome, and recording the status. Human readability and machine parseability are equally prioritized.

## 2. The Routing Matrix
Before beginning work, the agent must categorize the user's request using this matrix to determine the required Skill, Role, and Validation Gate.

| Request Type | Activated Skill | Assumed Role | Validation Gate (Terminal Commands) |
| :--- | :--- | :--- | :--- |
| **Feature Addition** | `feature-scaffold` | Architect + Developer | `npm run build` && `npm run test:unit` |
| **Bug Fix** | `debug-trace` | QA + Developer | `npm run test:failing` (must pass) |
| **Refactoring** | `dry-refactor` | Code Reviewer | `npm run lint` && `npm run test:all` |
| **Arch Change** | `sys-design` | Principal Architect | ADR approved by Human |
| **Doc Update** | `docs-sync` | Tech Writer | `npm run docs:build` |

## 3. Skill Activation 
Instead of relying on base model knowledge, the agent must explicitly invoke focused, task-specific instructions based on the Routing Matrix.
*   **Constraint:** Do not load all knowledge at once. Load only the relevant Skill definition for the current AWP.
*   **Behavior:** If a task spans multiple skills, break it into sequential AWPs.

## 4. AWP Lifecycle (Strict Steps)
The agent must execute every request following these four immutable steps:

### Phase 1: AWP Definition (Plan)
Generate an `awp-{id}.md` file in the `.agents/awp/active/` directory containing:
- **Scope:** Exact files to be modified (no external files may be touched).
- **Goal:** One-sentence objective.
- **Acceptance Criteria:** 3-5 bullet points.

### Phase 2: ADR Generation (If Architectural)
If the task involves adding new dependencies, changing data schemas, or altering system architecture, generate an `adr-{date}-{topic}.md` in `/docs/adr/`.
- Must contain: *Context, Decision, Consequences.*
- **PAUSE:** Wait for human approval on the ADR before coding.

### Phase 3: Execution & Validation Gate
Write the code restricted strictly to the defined AWP scope. 
Once written, execute the Validation Gate commands defined in the Routing Matrix.
- **Rule:** The AWP is NOT complete until the Validation Gate commands exit with code `0`.
- **Rule:** If the gate fails 3 times, halt and request human intervention.

### Phase 4: Status Report (Audit Trail)
Upon successful validation, append a record to `.agents/status-ledger.json` (for machines) and output a brief summary in the chat (for humans):
- Files changed.
- Validation commands run + their output status.
- Next recommended AWP (if any).
Move the AWP file to `.agents/awp/completed/`.

---

## 5. Dynamic Skill Activation (The Trigger Engine)

Loading all knowledge at once bloats the context window and causes hallucinations. Instead, skills should live in your repository as isolated folders (e.g., `.agents/skills/[skill-name]/SKILL.md`), loaded on demand based on context.

**How it works:**
The agent runs a lightweight "Triage Loop" before touching code. It evaluates the current AWP against four trigger types to decide which skills to inject into its context:

* **Filepath Triggers:** If the AWP touches `*.tf` or `aws/**/*.py`, automatically load the `infrastructure-as-code` skill.
* **Error Signature Triggers:** If the Validation Gate fails with `psycopg2.OperationalError`, load the `db-connection-troubleshooting` skill.
* **Tooling Triggers:** If the AWP requires creating an architectural diagram, load the `mermaid-diagram-generation` skill.
* **Semantic Intent:** If the user prompt implies a specific goal ("optimize this query"), semantic matching selects the `sql-optimization` skill.

*Workflow Rule:* The agent may only have a maximum of two active skills loaded at any given time to prevent instruction conflict.

## 6. Skill Auto-Creation (The "Session Lift" Workflow)

Agents should not invent skills out of thin air. Instead, they should **extract** skills from successful, hard-won sessions. When an agent figures out how to solve a novel problem, that procedural memory must be preserved.

**The Trigger:**

* An AWP takes more than 3 attempts to pass the Validation Gate, but eventually succeeds.
* The human explicitly types `/extract-skill` after a successful interaction.

**The Action (Agent runs the Extract-Skill AWP):**

1. **Analyze Transcript:** The agent reviews the terminal history and code diffs of the just-completed AWP.
2. **Filter Noise:** It strips out the failed attempts and isolates the exact sequence of tool calls and code changes that led to the `exit 0` success.
3. **Generate `SKILL.md`:** The agent drafts a new skill file containing:
* **YAML Frontmatter:** Defining the triggers (when this skill should be used).
* **Procedure:** The verified step-by-step fix.
* **Troubleshooting:** The dead-ends to avoid (learned from the failed attempts).

4. **Save to Drafts:** The skill is saved to `.agents/skills/drafts/`.

**The Validation Gate:**
A human reviews the draft markdown file. If accurate, they move it to `.agents/skills/active/` and append its triggers to the Routing Matrix.

## 7. Continuous Improvement (The Retrospective Workflow)

Your machine-readable `status-ledger.json` is an audit trail that can be mined to improve the AI's future performance.

**The Workflow:**
Create a dedicated AWP called the **"Ledger Retrospective"** that runs weekly or after every major milestone.

1. **Read the Ledger:** A meta-agent parses the JSON status ledger.
2. **Identify Bottlenecks:** It looks for patterns. (e.g., "The `feature-scaffold` skill failed its validation gate 40% of the time this week, specifically during testing.")
3. **Propose Updates:** The meta-agent generates a pull request updating the `feature-scaffold` SKILL.md file with stricter testing guidelines or new troubleshooting steps.