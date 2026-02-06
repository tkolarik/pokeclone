import io
import json

import pytest

import server


def _build_handler(path, payload_bytes=b"", content_length_header=None):
    handler = server.KanbanHandler.__new__(server.KanbanHandler)
    handler.path = path
    handler.headers = {}
    if content_length_header is not None:
        handler.headers["Content-Length"] = content_length_header
    handler.rfile = io.BytesIO(payload_bytes)
    responses = []
    handler._send_json = lambda code, payload: responses.append((code, payload))
    return handler, responses


def test_generate_unique_task_id_skips_existing_and_manual_ids():
    generated = server.generate_unique_task_id(
        [
            {"id": "TASK-1"},
            {"id": "TASK-3"},
            {"id": "CUSTOM-42"},
        ]
    )
    assert generated == "TASK-2"


def test_validate_task_payload_rejects_unknown_field():
    with pytest.raises(server.ApiError) as error:
        server.validate_task_payload(
            {
                "title": "Unknown Field",
                "status": "To Do",
                "priority": "Medium",
                "type": "Task",
                "bogus": True,
            }
        )

    assert error.value.status_code == 400
    assert "Unknown field" in error.value.message


def test_validate_task_payload_rejects_invalid_status():
    with pytest.raises(server.ApiError) as error:
        server.validate_task_payload(
            {
                "title": "Bad Status",
                "status": "Working",
                "priority": "Medium",
                "type": "Task",
            }
        )

    assert error.value.status_code == 400
    assert "Invalid status" in error.value.message


def test_post_rejects_duplicate_id():
    payload = {
        "id": "TASK-1",
        "title": "Duplicate",
        "status": "To Do",
        "priority": "Medium",
        "type": "Task",
    }
    body = json.dumps(payload).encode("utf-8")
    handler, responses = _build_handler(
        "/api/tasks",
        payload_bytes=body,
        content_length_header=str(len(body)),
    )
    handler._load_tasks = lambda: [
        {
            "id": "TASK-1",
            "title": "Existing",
            "status": "To Do",
            "priority": "Medium",
            "type": "Task",
        }
    ]
    handler._save_tasks = lambda tasks: pytest.fail("duplicate id should not be saved")

    handler.do_POST()

    status, response = responses[0]
    assert status == 409
    assert "already exists" in response["error"]


def test_post_generates_collision_safe_id_and_persists():
    payload = {
        "title": "Generated",
        "status": "To Do",
        "priority": "Medium",
        "type": "Task",
    }
    body = json.dumps(payload).encode("utf-8")
    handler, responses = _build_handler(
        "/api/tasks",
        payload_bytes=body,
        content_length_header=str(len(body)),
    )

    existing_tasks = [
        {"id": "TASK-1", "title": "One", "status": "To Do", "priority": "High", "type": "Task"},
        {
            "id": "TASK-3",
            "title": "Three",
            "status": "To Do",
            "priority": "High",
            "type": "Task",
        },
    ]
    handler._load_tasks = lambda: [dict(task) for task in existing_tasks]
    persisted = {}

    def _save_tasks(tasks):
        persisted["tasks"] = tasks

    handler._save_tasks = _save_tasks

    handler.do_POST()

    status, response = responses[0]
    assert status == 201
    assert response["id"] == "TASK-2"
    assert any(task["id"] == "TASK-2" for task in persisted["tasks"])


def test_read_json_body_rejects_missing_content_length():
    handler, _ = _build_handler("/api/tasks", payload_bytes=b'{"status":"Done"}')

    with pytest.raises(server.ApiError) as error:
        handler._read_json_body()

    assert error.value.status_code == 411
    assert "Missing Content-Length" in error.value.message


def test_read_json_body_rejects_invalid_content_length():
    handler, _ = _build_handler(
        "/api/tasks",
        payload_bytes=b'{"status":"Done"}',
        content_length_header="abc",
    )

    with pytest.raises(server.ApiError) as error:
        handler._read_json_body()

    assert error.value.status_code == 400
    assert "Invalid Content-Length" in error.value.message


def test_read_json_body_rejects_malformed_json():
    malformed = b'{"title":"broken}'
    handler, _ = _build_handler(
        "/api/tasks",
        payload_bytes=malformed,
        content_length_header=str(len(malformed)),
    )

    with pytest.raises(server.ApiError) as error:
        handler._read_json_body()

    assert error.value.status_code == 400
    assert "Malformed JSON" in error.value.message


def test_put_returns_not_found_for_missing_task():
    payload = {"status": "Done"}
    body = json.dumps(payload).encode("utf-8")
    handler, responses = _build_handler(
        "/api/tasks/TASK-999",
        payload_bytes=body,
        content_length_header=str(len(body)),
    )
    handler._load_tasks = lambda: []
    handler._save_tasks = lambda tasks: pytest.fail("missing task should not be saved")

    handler.do_PUT()

    status, response = responses[0]
    assert status == 404
    assert response["error"] == "Task 'TASK-999' not found."


def test_put_rejects_invalid_priority():
    payload = {"priority": "Urgent"}
    body = json.dumps(payload).encode("utf-8")
    handler, responses = _build_handler(
        "/api/tasks/TASK-1",
        payload_bytes=body,
        content_length_header=str(len(body)),
    )
    handler._load_tasks = lambda: [
        {"id": "TASK-1", "title": "Existing", "status": "To Do", "priority": "Medium", "type": "Task"}
    ]
    handler._save_tasks = lambda tasks: pytest.fail("invalid payload should not be saved")

    handler.do_PUT()

    status, response = responses[0]
    assert status == 400
    assert "Invalid priority" in response["error"]
