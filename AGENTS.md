# PokeClone — Agent Rules (must follow)

This repo is a Pygame-based monster battling game + tooling (pixel art editor, move animation editor, overworld/map editor) with a JSON Kanban board (`tasks.json`). The goal of this file is to make agents reliable across long tasks: always runnable, always test-gated, and resistant to “retry loops”.

---

## Goal

Build and improve **PokeClone** while preserving:
- A runnable game experience (main menu → battle / overworld where applicable)
- Reliable editors (pixel art, move animation, map editor)
- A working Kanban workflow (`tasks.json` + optional API)

---

## Non-negotiables

- **Always keep the project runnable.**
- **Every ticket ends with:**
  1) tests run (exact command + result)  
  2) how to verify manually (exact steps / what to click / what to observe)
- **Never implement large features without:**
  - a short plan
  - acceptance criteria (measurable bullets)
- **No silent “done”.** If something is partially done, mark it **On Hold** and log blockers.

---

## Session recovery (do this first every session)

1) Read:
   - `/notes/progress.md`
   - `/notes/decisions.md`
   - `/notes/blockers.md`
   - If these files don’t exist, **create them** (empty templates are fine).
2) Check `tasks.json` for the next **To Do** or **In Progress** task.
3) `git status` + skim recent commits (`git log -n 10 --oneline`).
4) Continue the next unfinished task with the smallest safe increment.

---

## Work loop

**PLAN → IMPLEMENT → TEST → DOCUMENT → COMMIT**

### PLAN
- Write a short plan in the ticket or task notes.
- Define **acceptance criteria** (bullets, measurable).
- Identify risky unknowns early (APIs, file formats, Pygame edge cases, etc.).

### IMPLEMENT
- Keep diffs small and modular.
- Prefer data-driven behavior (JSON/config) over hardcoding.
- Avoid “mega scripts” and sprawling refactors.

### TEST (must happen before marking Done)
- Run the automated tests (see “Running tests”).
- Run the relevant app entrypoint and manually verify the feature.

### DOCUMENT
After finishing work, update:
- `/notes/progress.md`: what changed + next steps
- `/notes/decisions.md`: any architectural decisions + rationale
- `/notes/blockers.md`: anything unresolved + attempt counts (see loop-breaking)

### COMMIT
- Commit with a message that references the work item when possible (e.g., `TASK-17: ...`).
- Do not mix unrelated changes in one commit.

---

## Loop-breaking (required)

Agents waste hours by retrying the same fix. We prevent that with explicit counters + timeboxing.

### Retry logging (required)
For any repeated failure, log to `/notes/blockers.md` using this format:

- **Issue:** short name
- **Context:** where/what
- **Attempt count:** N (increment every retry)
- **Last error / symptom:** paste the key error line(s)
- **What changed this attempt:** 1–3 bullets
- **Next approach:** what you will do differently

### Hard rules
- **After 3 failed attempts** on the same issue:
  - stop doing the same thing
  - pick a *different* approach (simplify, add a test, bisect, revert, isolate repro, etc.)
- **After ~20 minutes** stuck on one issue (or 5 attempts, whichever comes first):
  - log it as a blocker
  - move to a smaller parallel task **or** request human input (clearly state what you need)
- **If you notice repeated work you already did:**
  - re-read `/notes/progress.md`
  - check recent commits
  - reconcile what’s already implemented before proceeding

---

## Kanban board (source of truth: `tasks.json`)

The project tasks are managed via a JSON-based Kanban board. :contentReference[oaicite:1]{index=1}

### Method 1: Direct file manipulation (preferred for local agents)
1. Read `tasks.json`.
2. Parse the JSON list.
3. Modify the list (add object, update status, etc.).
4. Write the list back to `tasks.json`.

**Task schema (shape):**
```json
{
  "id": "TASK-1",
  "title": "Task Name",
  "status": "To Do",
  "priority": "Medium",
  "type": "Feature"
}
