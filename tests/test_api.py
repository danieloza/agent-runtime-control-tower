from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from agent_runtime_control_tower.main import create_app
from agent_runtime_control_tower.repository import SQLiteRepository
from agent_runtime_control_tower.state import InMemoryRuntimeStateStore


def make_client(tmp_path: Path) -> TestClient:
    app = create_app(SQLiteRepository(f"sqlite:///{tmp_path / 'tower.db'}"), InMemoryRuntimeStateStore())
    return TestClient(app)


def test_health_endpoint(tmp_path: Path) -> None:
    client = make_client(tmp_path)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["service"] == "agent-runtime-control-tower"
    assert response.json()["database_backend"] == "sqlite"
    assert response.json()["state_backend"] == "memory"


def test_run_request_requires_api_key(tmp_path: Path) -> None:
    client = make_client(tmp_path)

    response = client.post(
        "/runs",
        json={
            "agent_id": "agt_triage",
            "policy_id": "pol_ops_default",
            "mcp_server_id": "mcp_docs",
            "task_summary": "Summarize open support escalations.",
            "estimated_cost_usd": 3.0,
            "tool_calls_count": 2,
        },
    )

    assert response.status_code == 401


def test_safe_run_is_approved_via_api(tmp_path: Path) -> None:
    client = make_client(tmp_path)

    response = client.post(
        "/runs",
        headers={"X-API-Key": "art-ops-demo"},
        json={
            "agent_id": "agt_triage",
            "policy_id": "pol_ops_default",
            "mcp_server_id": "mcp_docs",
            "task_summary": "Summarize open support escalations.",
            "estimated_cost_usd": 3.0,
            "tool_calls_count": 2,
        },
    )

    assert response.status_code == 201
    assert response.json()["status"] == "approved"


def test_risky_run_creates_pending_approval_via_api(tmp_path: Path) -> None:
    client = make_client(tmp_path)

    create_response = client.post(
        "/runs",
        headers={"X-API-Key": "art-ops-demo"},
        json={
            "agent_id": "agt_triage",
            "policy_id": "pol_ops_default",
            "mcp_server_id": "mcp_docs",
            "task_summary": "Investigate a large backlog with expanded tooling.",
            "estimated_cost_usd": 20.0,
            "tool_calls_count": 9,
        },
    )

    approvals_response = client.get("/approvals", headers={"X-API-Key": "art-ops-demo"})

    assert create_response.status_code == 201
    assert create_response.json()["status"] == "awaiting_approval"
    assert approvals_response.status_code == 200
    assert len(approvals_response.json()) == 1


def test_run_state_and_replay_endpoints(tmp_path: Path) -> None:
    client = make_client(tmp_path)

    create_response = client.post(
        "/runs",
        headers={"X-API-Key": "art-ops-demo"},
        json={
            "agent_id": "agt_triage",
            "policy_id": "pol_ops_default",
            "mcp_server_id": "mcp_docs",
            "task_summary": "Summarize support incidents for handoff.",
            "estimated_cost_usd": 4.0,
            "tool_calls_count": 2,
        },
    )
    run_id = create_response.json()["id"]

    state_response = client.get(f"/runs/{run_id}/state", headers={"X-API-Key": "art-ops-demo"})
    replay_response = client.post(
        f"/runs/{run_id}/replay",
        headers={"X-API-Key": "art-ops-demo"},
        json={"task_summary_suffix": "Replay validation"},
    )

    assert state_response.status_code == 200
    assert state_response.json()["status"] == "approved"
    assert replay_response.status_code == 201
    assert replay_response.json()["id"] != run_id
