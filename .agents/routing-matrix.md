# Routing Matrix

Before beginning work, categorize the user's request using this matrix to determine the required Skill, Role, and Validation Gate.

| Request Type | Activated Skill | Assumed Role | Validation Gate (Terminal Commands) |
| :--- | :--- | :--- | :--- |
| **Feature Addition** | `feature-scaffold` | Architect + Developer | `npm run build` && `npm run test:unit` |
| **Bug Fix** | `debug-trace` | QA + Developer | `npm run test:failing` (must pass) |
| **Refactoring** | `dry-refactor` | Code Reviewer | `npm run lint` && `npm run test:all` |
| **Arch Change** | `sys-design` | Principal Architect | ADR approved by Human |
| **Doc Update** | `docs-sync` | Tech Writer | `npm run docs:build` |
