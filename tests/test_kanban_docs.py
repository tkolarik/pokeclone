from pathlib import Path

import server


def test_agents_md_matches_runtime_api_port_and_endpoint():
    agents_text = Path("AGENTS.md").read_text(encoding="utf-8")

    expected_host = f"localhost:{server.PORT}"
    assert expected_host in agents_text
    assert "/api/tasks" in agents_text
    assert "localhost:8000" not in agents_text


def test_readme_includes_api_verification_command():
    readme_text = Path("README.md").read_text(encoding="utf-8")

    expected_check = f"curl -sf http://localhost:{server.PORT}/api/tasks"
    assert expected_check in readme_text
