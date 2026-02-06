# PokeClone Kanban API Instructions for AI Agents

The project tasks are managed via a JSON-based Kanban board.

## Data Source
The source of truth is `tasks.json`.

## Interaction Methods

### Method 1: Direct File Manipulation (Preferred for local agents)
1. Read `tasks.json`.
2. Parse the JSON list.
3. Modify the list (add object, update status, etc.).
4. Write the list back to `tasks.json`.

**Task Schema:**
{
  "id": "TASK-1",          // Unique String
  "title": "Task Name",    // String
  "status": "To Do",       // "To Do", "In Progress", "On Hold", "Done"
  "priority": "Medium",    // "Highest", "High", "Medium", "Low"
  "type": "Feature"        // String
}

### Method 2: REST API (If server is running)
If `python server.py` is running on localhost:8001:

- **List Tasks:** `GET http://localhost:8001/api/tasks`
- **Add Task:** `POST http://localhost:8001/api/tasks`
  - Body: JSON object (see schema above, `id` is optional/auto-generated)
- **Update Task:** `PUT http://localhost:8001/api/tasks/<TASK_ID>`
  - Body: JSON object with fields to update (e.g., `{"status": "Done"}`)
- **Verify API availability:** `curl -sf http://localhost:8001/api/tasks`

## Setup
To initialize the board from the legacy `ToDo.md`, run: `python convert.py`

## Running tests
Use the canonical test command:

- `./scripts/run_tests.sh`

If `.venv` is not prepared, bootstrap it first:

- `./scripts/bootstrap_test_env.sh`

If you need to use a specific interpreter (for example, Conda), run:

- `POKECLONE_TEST_PYTHON=/path/to/python ./scripts/run_tests.sh`

If `.venv` was created with an incompatible Python build (e.g., missing `pygame.mixer`), recreate it with Python 3.12:

- `POKECLONE_BOOTSTRAP_PYTHON=$(command -v python3.12) ./scripts/bootstrap_test_env.sh --recreate`

## Ticket quality rule
Every new ticket created must include automated unit testing in the acceptance criteria to the extent reasonable for the change.
