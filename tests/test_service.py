from __future__ import annotations

from pathlib import Path

from agent_runtime_control_tower.repository import SQLiteRepository
from agent_runtime_control_tower.services import RuntimeTowerService
from agent_runtime_control_tower.state import InMemoryRuntimeStateStore


def build_service(tmp_path: Path) -> RuntimeTowerService:
    repo = SQLiteRepository(f"sqlite:///{tmp_path / 'tower.db'}")
    return RuntimeTowerService(repo, InMemoryRuntimeStateStore())


def test_safe_run_is_auto_approved(tmp_path: Path) -> None:
    service = build_service(tmp_path)
    auth = service.build_auth_context("art-ops-demo")
    assert auth is not None

    run = service.request_run(
        auth,
        agent_id="agt_triage",
        policy_id="pol_ops_default",
        mcp_server_id="mcp_docs",
        task_summary="Summarize open support escalations.",
        estimated_cost_usd=3.5,
        tool_calls_count=2,
    )

    assert run.status == "approved"
    assert run.approval_id is None


def test_sensitive_server_is_blocked_and_creates_incident(tmp_path: Path) -> None:
    service = build_service(tmp_path)
    auth = service.build_auth_context("art-admin-demo")
    assert auth is not None

    run = service.request_run(
        auth,
        agent_id="agt_triage",
        policy_id="pol_ops_default",
        mcp_server_id="mcp_finance",
        task_summary="Try reading finance ledger snapshots.",
        estimated_cost_usd=3.0,
        tool_calls_count=2,
    )

    incidents = service.list_incidents(auth)
    assert run.status == "blocked"
    assert incidents
    assert incidents[0].run_id == run.id


def test_risky_run_routes_to_approval(tmp_path: Path) -> None:
    service = build_service(tmp_path)
    auth = service.build_auth_context("art-ops-demo")
    assert auth is not None

    run = service.request_run(
        auth,
        agent_id="agt_triage",
        policy_id="pol_ops_default",
        mcp_server_id="mcp_docs",
        task_summary="Investigate a large backlog with expanded tooling.",
        estimated_cost_usd=25.0,
        tool_calls_count=11,
    )

    approvals = service.list_pending_approvals(auth)
    assert run.status == "awaiting_approval"
    assert approvals
    assert approvals[0].run_id == run.id


def test_security_admin_can_approve(tmp_path: Path) -> None:
    service = build_service(tmp_path)
    operator = service.build_auth_context("art-admin-demo")
    reviewer = service.build_auth_context("art-security-demo")
    assert operator is not None
    assert reviewer is not None

    run = service.request_run(
        operator,
        agent_id="agt_finops",
        policy_id="pol_finance_guarded",
        mcp_server_id="mcp_finance",
        task_summary="Review vendor variance against monthly budget.",
        estimated_cost_usd=8.0,
        tool_calls_count=3,
    )
    assert run.approval_id is not None

    approval = service.decide_approval(reviewer, run.approval_id, "approved")
    assert approval.status == "approved"


def test_run_state_and_replay_are_available(tmp_path: Path) -> None:
    service = build_service(tmp_path)
    auth = service.build_auth_context("art-ops-demo")
    assert auth is not None

    run = service.request_run(
        auth,
        agent_id="agt_triage",
        policy_id="pol_ops_default",
        mcp_server_id="mcp_docs",
        task_summary="Summarize support incidents for handoff.",
        estimated_cost_usd=4.0,
        tool_calls_count=2,
    )

    state = service.get_run_state(auth, run.id)
    replay = service.replay_run(auth, run.id, task_summary_suffix="Dry run replay")

    assert state["status"] == "approved"
    assert state["state_backend"] == "memory"
    assert replay.id != run.id
