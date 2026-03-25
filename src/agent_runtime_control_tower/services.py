from __future__ import annotations

from dataclasses import dataclass

from agent_runtime_control_tower.models import AgentRun, ApprovalItem, Incident, ToolCallTrace, User
from agent_runtime_control_tower.repository import ControlTowerRepository
from agent_runtime_control_tower.state import RuntimeStateStore


@dataclass(slots=True)
class AuthContext:
    user: User
    organization_id: str | None


class RuntimeTowerService:
    def __init__(self, repo: ControlTowerRepository, state_store: RuntimeStateStore) -> None:
        self.repo = repo
        self.state_store = state_store

    def build_auth_context(self, api_key: str) -> AuthContext | None:
        user = self.repo.get_user_by_api_key(api_key)
        if not user:
            return None
        return AuthContext(user=user, organization_id=user.organization_id)

    def list_organizations(self, auth: AuthContext):
        if auth.user.role == "platform_admin":
            return self.repo.list_organizations()
        if auth.organization_id:
            organization = self.repo.get_organization(auth.organization_id)
            return [organization] if organization else []
        return []

    def list_mcp_servers(self, auth: AuthContext):
        return self.repo.list_mcp_servers(auth.organization_id)

    def list_agents(self, auth: AuthContext):
        return self.repo.list_agents(auth.organization_id)

    def list_policies(self, auth: AuthContext):
        return self.repo.list_policies(auth.organization_id)

    def list_runs(self, auth: AuthContext):
        return self.repo.list_runs(auth.organization_id)

    def list_pending_approvals(self, auth: AuthContext):
        return self.repo.list_approvals(auth.organization_id)

    def list_incidents(self, auth: AuthContext):
        return self.repo.list_incidents(auth.organization_id)

    def get_run_traces(self, auth: AuthContext, run_id: str):
        runs = {item.id: item for item in self.list_runs(auth)}
        if run_id not in runs:
            raise ValueError("Run not found for current scope.")
        return self.repo.list_tool_traces(run_id)

    def get_run_state(self, auth: AuthContext, run_id: str):
        runs = {item.id: item for item in self.list_runs(auth)}
        if run_id not in runs:
            raise ValueError("Run not found for current scope.")
        payload = self.state_store.get_run_state(run_id)
        if not payload:
            raise ValueError("Runtime state not found.")
        return payload

    def request_run(
        self,
        auth: AuthContext,
        *,
        agent_id: str,
        policy_id: str,
        mcp_server_id: str,
        task_summary: str,
        estimated_cost_usd: float,
        tool_calls_count: int,
    ) -> AgentRun:
        agent = self.repo.get_agent(agent_id)
        policy = self.repo.get_policy(policy_id)
        server = self.repo.get_mcp_server(mcp_server_id)

        if not agent or not policy or not server:
            raise ValueError("Agent, policy, or MCP server not found.")

        organization_id = auth.organization_id or agent.organization_id
        if auth.user.role != "platform_admin":
            if agent.organization_id != organization_id or policy.organization_id != organization_id or server.organization_id != organization_id:
                raise PermissionError("Cross-tenant access is not allowed.")

        risk_reasons: list[str] = []
        blocked = False

        if estimated_cost_usd > agent.max_budget_usd:
            risk_reasons.append("estimated budget exceeds agent cap")
        if tool_calls_count > policy.max_tool_calls:
            risk_reasons.append("tool call volume exceeds policy limit")
        if server.risk_tier in {"sensitive", "restricted"}:
            risk_reasons.append(f"target MCP risk tier is {server.risk_tier}")
        if policy.deny_sensitive_mcp and server.risk_tier in {"sensitive", "restricted"}:
            blocked = True
            risk_reasons.append("policy denies sensitive MCP targets")

        status = "approved"
        if blocked:
            status = "blocked"
        elif policy.requires_human_approval or agent.approval_required or risk_reasons:
            status = "awaiting_approval"

        approval_id: str | None = None
        run = AgentRun(
            id=self.repo.next_id("run", "agent_runs"),
            agent_id=agent.id,
            organization_id=agent.organization_id,
            policy_id=policy.id,
            mcp_server_id=server.id,
            requested_by=auth.user.id,
            task_summary=task_summary,
            status=status,
            risk_reason="; ".join(risk_reasons) if risk_reasons else "within normal operating envelope",
            tool_calls_count=tool_calls_count,
            estimated_cost_usd=estimated_cost_usd,
        )

        if status == "awaiting_approval":
            approval = ApprovalItem(
                id=self.repo.next_id("apr", "approvals"),
                run_id=run.id,
                organization_id=run.organization_id,
                requested_by=auth.user.id,
                reason=run.risk_reason,
            )
            approval_id = approval.id
            run.approval_id = approval.id
            self.repo.create_approval(approval)

        self.repo.create_run(run)
        self.repo.add_tool_trace(
            ToolCallTrace(
                id=self.repo.next_id("trc", "tool_call_traces"),
                run_id=run.id,
                tool_name="mcp.invoke",
                mcp_server_id=server.id,
                outcome="blocked" if status == "blocked" else "simulated",
                latency_ms=140,
            )
        )

        if status == "blocked":
            self.repo.add_incident(
                Incident(
                    id=self.repo.next_id("inc", "incidents"),
                    run_id=run.id,
                    organization_id=run.organization_id,
                    severity="high",
                    summary="Blocked run attempting access to policy-restricted MCP target.",
                )
            )

        if approval_id:
            self.repo.update_run_status(run.id, run.status, approval_id)

        self.state_store.upsert_run_state(
            run.id,
            {
                "run_id": run.id,
                "status": run.status,
                "approval_id": run.approval_id,
                "risk_reason": run.risk_reason,
                "estimated_cost_usd": run.estimated_cost_usd,
                "tool_calls_count": run.tool_calls_count,
                "state_backend": self.state_store.backend_name,
            },
        )

        return run

    def replay_run(
        self,
        auth: AuthContext,
        run_id: str,
        *,
        task_summary_suffix: str | None = None,
        override_policy_id: str | None = None,
        override_mcp_server_id: str | None = None,
    ) -> AgentRun:
        existing = self.repo.get_run(run_id)
        if not existing:
            raise ValueError("Run not found.")
        if auth.user.role != "platform_admin" and existing.organization_id != auth.organization_id:
            raise PermissionError("Cross-tenant replay is not allowed.")
        suffix = task_summary_suffix or "Replay validation run"
        return self.request_run(
            auth,
            agent_id=existing.agent_id,
            policy_id=override_policy_id or existing.policy_id,
            mcp_server_id=override_mcp_server_id or existing.mcp_server_id,
            task_summary=f"{existing.task_summary} [{suffix}]",
            estimated_cost_usd=existing.estimated_cost_usd,
            tool_calls_count=existing.tool_calls_count,
        )

    def decide_approval(self, auth: AuthContext, approval_id: str, decision: str) -> ApprovalItem:
        if auth.user.role not in {"platform_admin", "security_admin"}:
            raise PermissionError("Only platform or security admins can decide approvals.")
        approval = self.repo.get_approval(approval_id)
        if not approval:
            raise ValueError("Approval not found.")
        if auth.user.role != "platform_admin" and approval.organization_id != auth.organization_id:
            raise PermissionError("Cross-tenant approval decision is not allowed.")
        if decision not in {"approved", "rejected"}:
            raise ValueError("Unsupported approval decision.")

        self.repo.set_approval_decision(approval_id, decision, auth.user.id)
        self.repo.update_run_status(approval.run_id, "approved" if decision == "approved" else "blocked")
        self.state_store.upsert_run_state(
            approval.run_id,
            {
                "run_id": approval.run_id,
                "status": "approved" if decision == "approved" else "blocked",
                "approval_id": approval.id,
                "decided_by": auth.user.id,
                "decision": decision,
                "state_backend": self.state_store.backend_name,
            },
        )
        updated = self.repo.get_approval(approval_id)
        if not updated:
            raise ValueError("Approval update failed.")
        return updated

    def health_snapshot(self) -> dict[str, int | str]:
        return {**self.repo.health_snapshot(), "state_backend": self.state_store.backend_name}
