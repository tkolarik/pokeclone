import http.server
import json
import os
import socketserver

PORT = 8001
DATA_FILE = os.path.join(os.path.dirname(__file__), "tasks.json")

ALLOWED_STATUSES = {"To Do", "In Progress", "On Hold", "Done"}
ALLOWED_PRIORITIES = {"Highest", "High", "Medium", "Low"}
ALLOWED_TYPES = {"Task", "Feature", "Improvement"}

REQUIRED_CREATE_FIELDS = {"title", "status", "priority", "type"}
OPTIONAL_FIELDS = {
    "id",
    "labels",
    "description",
    "acceptanceCriteria",
    "dependsOn",
    "fields",
    "comments",
}
ALLOWED_FIELDS = REQUIRED_CREATE_FIELDS | OPTIONAL_FIELDS


class ApiError(Exception):
    def __init__(self, status_code, message):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


def generate_unique_task_id(tasks):
    existing_ids = {task.get("id") for task in tasks if isinstance(task, dict)}
    next_index = 1
    while f"TASK-{next_index}" in existing_ids:
        next_index += 1
    return f"TASK-{next_index}"


def _require_non_empty_string(payload, field_name):
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ApiError(400, f"Field '{field_name}' must be a non-empty string.")
    return value


def validate_task_payload(payload, *, for_update=False):
    if not isinstance(payload, dict):
        raise ApiError(400, "JSON payload must be an object.")

    unknown_fields = sorted(set(payload) - ALLOWED_FIELDS)
    if unknown_fields:
        raise ApiError(400, f"Unknown field(s): {', '.join(unknown_fields)}")

    if for_update:
        if not payload:
            raise ApiError(400, "Update payload must include at least one field.")
        if "id" in payload:
            raise ApiError(400, "Task ID cannot be updated.")
    else:
        missing_required = sorted(
            field
            for field in REQUIRED_CREATE_FIELDS
            if field not in payload
            or payload[field] is None
            or (isinstance(payload[field], str) and not payload[field].strip())
        )
        if missing_required:
            raise ApiError(
                400, f"Missing required field(s): {', '.join(missing_required)}"
            )
        if "id" in payload and payload["id"] is not None:
            _require_non_empty_string(payload, "id")

    if "title" in payload:
        _require_non_empty_string(payload, "title")

    if "status" in payload:
        status = _require_non_empty_string(payload, "status")
        if status not in ALLOWED_STATUSES:
            raise ApiError(
                400,
                f"Invalid status '{status}'. Allowed values: "
                + ", ".join(sorted(ALLOWED_STATUSES)),
            )

    if "priority" in payload:
        priority = _require_non_empty_string(payload, "priority")
        if priority not in ALLOWED_PRIORITIES:
            raise ApiError(
                400,
                f"Invalid priority '{priority}'. Allowed values: "
                + ", ".join(sorted(ALLOWED_PRIORITIES)),
            )

    if "type" in payload:
        task_type = _require_non_empty_string(payload, "type")
        if task_type not in ALLOWED_TYPES:
            raise ApiError(
                400,
                f"Invalid type '{task_type}'. Allowed values: "
                + ", ".join(sorted(ALLOWED_TYPES)),
            )

    return payload


class KanbanHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/tasks":
            try:
                self._send_json(200, self._load_tasks())
            except (OSError, json.JSONDecodeError, ApiError) as exc:
                self._send_json(500, {"error": f"Failed to load tasks: {exc}"})
            return
        if self.path == "/":
            self.path = "/index.html"
        super().do_GET()

    def do_POST(self):
        if self.path != "/api/tasks":
            self._send_json(404, {"error": "Endpoint not found."})
            return

        try:
            new_task = self._read_json_body()
            if "id" in new_task and (
                new_task["id"] is None
                or (isinstance(new_task["id"], str) and not new_task["id"].strip())
            ):
                new_task.pop("id")
            validate_task_payload(new_task, for_update=False)

            tasks = self._load_tasks()

            if "id" not in new_task:
                new_task["id"] = generate_unique_task_id(tasks)
            elif any(task.get("id") == new_task["id"] for task in tasks):
                raise ApiError(409, f"Task with id '{new_task['id']}' already exists.")

            tasks.append(new_task)
            self._save_tasks(tasks)
            self._send_json(201, new_task)
        except ApiError as exc:
            self._send_json(exc.status_code, {"error": exc.message})
        except (OSError, json.JSONDecodeError) as exc:
            self._send_json(500, {"error": f"Failed to persist task: {exc}"})

    def do_PUT(self):
        if not self.path.startswith("/api/tasks/"):
            self._send_json(404, {"error": "Endpoint not found."})
            return

        task_id = self.path.split("/")[-1]
        if not task_id:
            self._send_json(404, {"error": "Task ID is required in the URL."})
            return

        try:
            updated_data = self._read_json_body()
            validate_task_payload(updated_data, for_update=True)

            tasks = self._load_tasks()
            for task in tasks:
                if task.get("id") == task_id:
                    task.update(updated_data)
                    self._save_tasks(tasks)
                    self._send_json(200, {"status": "updated", "id": task_id})
                    return

            self._send_json(404, {"error": f"Task '{task_id}' not found."})
        except ApiError as exc:
            self._send_json(exc.status_code, {"error": exc.message})
        except (OSError, json.JSONDecodeError) as exc:
            self._send_json(500, {"error": f"Failed to persist task update: {exc}"})

    def _read_json_body(self):
        content_length_value = self.headers.get("Content-Length")
        if content_length_value is None:
            raise ApiError(411, "Missing Content-Length header.")

        try:
            content_length = int(content_length_value)
        except (TypeError, ValueError):
            raise ApiError(400, "Invalid Content-Length header.")

        if content_length <= 0:
            raise ApiError(400, "Request body is required.")

        raw_body = self.rfile.read(content_length)
        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError:
            raise ApiError(400, "Malformed JSON request body.")

        if not isinstance(payload, dict):
            raise ApiError(400, "JSON payload must be an object.")
        return payload

    def _send_json(self, status_code, payload):
        response = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def _load_tasks(self):
        if not os.path.exists(DATA_FILE):
            return []
        with open(DATA_FILE, "r", encoding="utf-8") as data_stream:
            tasks = json.load(data_stream)
        if not isinstance(tasks, list):
            raise ApiError(500, "Task storage must contain a JSON array.")
        return tasks

    def _save_tasks(self, tasks):
        with open(DATA_FILE, "w", encoding="utf-8") as data_stream:
            json.dump(tasks, data_stream, indent=2)


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as data_stream:
            json.dump([], data_stream)

    with socketserver.TCPServer(("", PORT), KanbanHandler) as httpd:
        print(f"Serving Kanban Board at http://localhost:{PORT}")
        print("Press Ctrl+C to stop.")
        httpd.serve_forever()
