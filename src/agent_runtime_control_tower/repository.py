from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, Row

from agent_runtime_control_tower.config import default_database_url
from agent_runtime_control_tower.models import Agent, AgentRun, ApprovalItem, Incident, MCPServer, Organization, RuntimePolicy, ToolCallTrace, User
from agent_runtime_control_tower.seed_data import SEED_AGENTS, SEED_MCP_SERVERS, SEED_ORGANIZATIONS, SEED_POLICIES, SEED_USERS


class ControlTowerRepository:
    def __init__(self, database_url: str) -> None:
        connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
        self.database_url = database_url
        self.engine: Engine = create_engine(database_url, future=True, connect_args=connect_args)
        self._init_schema()
        self._seed_if_empty()

    def _connect(self):
        return self.engine.connect()

    def _init_schema(self) -> None:
        statements = [
            "CREATE TABLE IF NOT EXISTS organizations (id TEXT PRIMARY KEY, name TEXT NOT NULL, plan TEXT NOT NULL)",
            "CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, name TEXT NOT NULL, organization_id TEXT NULL, role TEXT NOT NULL, api_key TEXT NOT NULL UNIQUE)",
            "CREATE TABLE IF NOT EXISTS mcp_servers (id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, name TEXT NOT NULL, transport TEXT NOT NULL, auth_mode TEXT NOT NULL, risk_tier TEXT NOT NULL)",
            "CREATE TABLE IF NOT EXISTS agents (id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, name TEXT NOT NULL, runtime TEXT NOT NULL, max_budget_usd REAL NOT NULL, approval_required INTEGER NOT NULL)",
            "CREATE TABLE IF NOT EXISTS runtime_policies (id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, name TEXT NOT NULL, requires_human_approval INTEGER NOT NULL, max_tool_calls INTEGER NOT NULL, deny_sensitive_mcp INTEGER NOT NULL, allow_redis_memory INTEGER NOT NULL)",
            "CREATE TABLE IF NOT EXISTS agent_runs (id TEXT PRIMARY KEY, agent_id TEXT NOT NULL, organization_id TEXT NOT NULL, policy_id TEXT NOT NULL, mcp_server_id TEXT NOT NULL, requested_by TEXT NOT NULL, task_summary TEXT NOT NULL, status TEXT NOT NULL, risk_reason TEXT NOT NULL, tool_calls_count INTEGER NOT NULL, estimated_cost_usd REAL NOT NULL, approval_id TEXT NULL, created_at TEXT NOT NULL)",
            "CREATE TABLE IF NOT EXISTS approvals (id TEXT PRIMARY KEY, run_id TEXT NOT NULL, organization_id TEXT NOT NULL, requested_by TEXT NOT NULL, reason TEXT NOT NULL, status TEXT NOT NULL, decided_by TEXT NULL, created_at TEXT NOT NULL)",
            "CREATE TABLE IF NOT EXISTS tool_call_traces (id TEXT PRIMARY KEY, run_id TEXT NOT NULL, tool_name TEXT NOT NULL, mcp_server_id TEXT NOT NULL, outcome TEXT NOT NULL, latency_ms INTEGER NOT NULL)",
            "CREATE TABLE IF NOT EXISTS incidents (id TEXT PRIMARY KEY, run_id TEXT NOT NULL, organization_id TEXT NOT NULL, severity TEXT NOT NULL, summary TEXT NOT NULL, created_at TEXT NOT NULL)",
        ]
        with self.engine.begin() as connection:
            for statement in statements:
                connection.execute(text(statement))

    def _seed_if_empty(self) -> None:
        with self.engine.begin() as connection:
            if connection.execute(text("SELECT COUNT(*) FROM organizations")).scalar():
                return
            connection.execute(text("INSERT INTO organizations (id, name, plan) VALUES (:id, :name, :plan)"), [asdict(item) for item in SEED_ORGANIZATIONS])
            connection.execute(text("INSERT INTO users (id, name, organization_id, role, api_key) VALUES (:id, :name, :organization_id, :role, :api_key)"), [asdict(item) for item in SEED_USERS])
            connection.execute(text("INSERT INTO mcp_servers (id, organization_id, name, transport, auth_mode, risk_tier) VALUES (:id, :organization_id, :name, :transport, :auth_mode, :risk_tier)"), [asdict(item) for item in SEED_MCP_SERVERS])
            connection.execute(
                text("INSERT INTO agents (id, organization_id, name, runtime, max_budget_usd, approval_required) VALUES (:id, :organization_id, :name, :runtime, :max_budget_usd, :approval_required)"),
                [{**asdict(item), "approval_required": int(item.approval_required)} for item in SEED_AGENTS],
            )
            connection.execute(
                text("INSERT INTO runtime_policies (id, organization_id, name, requires_human_approval, max_tool_calls, deny_sensitive_mcp, allow_redis_memory) VALUES (:id, :organization_id, :name, :requires_human_approval, :max_tool_calls, :deny_sensitive_mcp, :allow_redis_memory)"),
                [{**asdict(item), "requires_human_approval": int(item.requires_human_approval), "deny_sensitive_mcp": int(item.deny_sensitive_mcp), "allow_redis_memory": int(item.allow_redis_memory)} for item in SEED_POLICIES],
            )

    def next_id(self, prefix: str, table: str, column: str = "id") -> str:
        with self._connect() as connection:
            row = connection.execute(
                text(f"SELECT {column} AS value FROM {table} WHERE {column} LIKE :pattern ORDER BY {column} DESC LIMIT 1"),
                {"pattern": f"{prefix}_%"},
            ).mappings().first()
        if not row:
            return f"{prefix}_0001"
        current = int(str(row["value"]).split("_")[-1])
        return f"{prefix}_{current + 1:04d}"

    def _first(self, query: str, params: dict[str, Any]) -> Row[Any] | None:
        with self._connect() as connection:
            return connection.execute(text(query), params).mappings().first()

    def _list(self, query: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(text(query), params or {}).mappings().all()
        return [dict(row) for row in rows]

    def get_user_by_api_key(self, api_key: str) -> User | None:
        row = self._first("SELECT * FROM users WHERE api_key = :api_key", {"api_key": api_key})
        return User(**dict(row)) if row else None

    def list_organizations(self) -> list[Organization]:
        return [Organization(**row) for row in self._list("SELECT * FROM organizations ORDER BY name")]

    def get_organization(self, organization_id: str) -> Organization | None:
        row = self._first("SELECT * FROM organizations WHERE id = :id", {"id": organization_id})
        return Organization(**dict(row)) if row else None

    def _list_rows(self, table: str, organization_id: str | None = None) -> list[dict[str, Any]]:
        query = f"SELECT * FROM {table}"
        params: dict[str, Any] = {}
        if organization_id:
            query += " WHERE organization_id = :organization_id"
            params["organization_id"] = organization_id
        query += " ORDER BY name"
        return self._list(query, params)

    def list_mcp_servers(self, organization_id: str | None = None) -> list[MCPServer]:
        return [MCPServer(**row) for row in self._list_rows("mcp_servers", organization_id)]

    def list_agents(self, organization_id: str | None = None) -> list[Agent]:
        rows = self._list_rows("agents", organization_id)
        return [Agent(id=row["id"], organization_id=row["organization_id"], name=row["name"], runtime=row["runtime"], max_budget_usd=row["max_budget_usd"], approval_required=bool(row["approval_required"])) for row in rows]

    def list_policies(self, organization_id: str | None = None) -> list[RuntimePolicy]:
        rows = self._list_rows("runtime_policies", organization_id)
        return [RuntimePolicy(id=row["id"], organization_id=row["organization_id"], name=row["name"], requires_human_approval=bool(row["requires_human_approval"]), max_tool_calls=row["max_tool_calls"], deny_sensitive_mcp=bool(row["deny_sensitive_mcp"]), allow_redis_memory=bool(row["allow_redis_memory"])) for row in rows]

    def get_agent(self, agent_id: str) -> Agent | None:
        row = self._first("SELECT * FROM agents WHERE id = :id", {"id": agent_id})
        return Agent(id=row["id"], organization_id=row["organization_id"], name=row["name"], runtime=row["runtime"], max_budget_usd=row["max_budget_usd"], approval_required=bool(row["approval_required"])) if row else None

    def get_mcp_server(self, server_id: str) -> MCPServer | None:
        row = self._first("SELECT * FROM mcp_servers WHERE id = :id", {"id": server_id})
        return MCPServer(**dict(row)) if row else None

    def get_policy(self, policy_id: str) -> RuntimePolicy | None:
        row = self._first("SELECT * FROM runtime_policies WHERE id = :id", {"id": policy_id})
        return RuntimePolicy(id=row["id"], organization_id=row["organization_id"], name=row["name"], requires_human_approval=bool(row["requires_human_approval"]), max_tool_calls=row["max_tool_calls"], deny_sensitive_mcp=bool(row["deny_sensitive_mcp"]), allow_redis_memory=bool(row["allow_redis_memory"])) if row else None

    def create_run(self, run: AgentRun) -> None:
        with self.engine.begin() as connection:
            connection.execute(
                text("INSERT INTO agent_runs (id, agent_id, organization_id, policy_id, mcp_server_id, requested_by, task_summary, status, risk_reason, tool_calls_count, estimated_cost_usd, approval_id, created_at) VALUES (:id, :agent_id, :organization_id, :policy_id, :mcp_server_id, :requested_by, :task_summary, :status, :risk_reason, :tool_calls_count, :estimated_cost_usd, :approval_id, :created_at)"),
                {**asdict(run), "created_at": run.created_at.isoformat()},
            )

    def update_run_status(self, run_id: str, status: str, approval_id: str | None = None) -> None:
        with self.engine.begin() as connection:
            connection.execute(
                text("UPDATE agent_runs SET status = :status, approval_id = COALESCE(:approval_id, approval_id) WHERE id = :run_id"),
                {"status": status, "approval_id": approval_id, "run_id": run_id},
            )

    def get_run(self, run_id: str) -> AgentRun | None:
        row = self._first("SELECT * FROM agent_runs WHERE id = :id", {"id": run_id})
        if not row:
            return None
        return AgentRun(
            id=row["id"],
            agent_id=row["agent_id"],
            organization_id=row["organization_id"],
            policy_id=row["policy_id"],
            mcp_server_id=row["mcp_server_id"],
            requested_by=row["requested_by"],
            task_summary=row["task_summary"],
            status=row["status"],
            risk_reason=row["risk_reason"],
            tool_calls_count=row["tool_calls_count"],
            estimated_cost_usd=row["estimated_cost_usd"],
            approval_id=row["approval_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def list_runs(self, organization_id: str | None = None) -> list[AgentRun]:
        query = "SELECT * FROM agent_runs"
        params: dict[str, Any] = {}
        if organization_id:
            query += " WHERE organization_id = :organization_id"
            params["organization_id"] = organization_id
        query += " ORDER BY created_at DESC"
        rows = self._list(query, params)
        return [
            AgentRun(
                id=row["id"],
                agent_id=row["agent_id"],
                organization_id=row["organization_id"],
                policy_id=row["policy_id"],
                mcp_server_id=row["mcp_server_id"],
                requested_by=row["requested_by"],
                task_summary=row["task_summary"],
                status=row["status"],
                risk_reason=row["risk_reason"],
                tool_calls_count=row["tool_calls_count"],
                estimated_cost_usd=row["estimated_cost_usd"],
                approval_id=row["approval_id"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]

    def create_approval(self, approval: ApprovalItem) -> None:
        with self.engine.begin() as connection:
            connection.execute(
                text("INSERT INTO approvals (id, run_id, organization_id, requested_by, reason, status, decided_by, created_at) VALUES (:id, :run_id, :organization_id, :requested_by, :reason, :status, :decided_by, :created_at)"),
                {**asdict(approval), "created_at": approval.created_at.isoformat()},
            )

    def list_approvals(self, organization_id: str | None = None) -> list[ApprovalItem]:
        query = "SELECT * FROM approvals WHERE status = 'pending'"
        params: dict[str, Any] = {}
        if organization_id:
            query += " AND organization_id = :organization_id"
            params["organization_id"] = organization_id
        query += " ORDER BY created_at DESC"
        rows = self._list(query, params)
        return [
            ApprovalItem(
                id=row["id"],
                run_id=row["run_id"],
                organization_id=row["organization_id"],
                requested_by=row["requested_by"],
                reason=row["reason"],
                status=row["status"],
                decided_by=row["decided_by"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]

    def get_approval(self, approval_id: str) -> ApprovalItem | None:
        row = self._first("SELECT * FROM approvals WHERE id = :id", {"id": approval_id})
        if not row:
            return None
        return ApprovalItem(
            id=row["id"],
            run_id=row["run_id"],
            organization_id=row["organization_id"],
            requested_by=row["requested_by"],
            reason=row["reason"],
            status=row["status"],
            decided_by=row["decided_by"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def set_approval_decision(self, approval_id: str, status: str, decided_by: str) -> None:
        with self.engine.begin() as connection:
            connection.execute(
                text("UPDATE approvals SET status = :status, decided_by = :decided_by WHERE id = :approval_id"),
                {"status": status, "decided_by": decided_by, "approval_id": approval_id},
            )

    def add_tool_trace(self, trace: ToolCallTrace) -> None:
        with self.engine.begin() as connection:
            connection.execute(
                text("INSERT INTO tool_call_traces (id, run_id, tool_name, mcp_server_id, outcome, latency_ms) VALUES (:id, :run_id, :tool_name, :mcp_server_id, :outcome, :latency_ms)"),
                asdict(trace),
            )

    def list_tool_traces(self, run_id: str) -> list[ToolCallTrace]:
        return [ToolCallTrace(**row) for row in self._list("SELECT * FROM tool_call_traces WHERE run_id = :run_id ORDER BY id", {"run_id": run_id})]

    def add_incident(self, incident: Incident) -> None:
        with self.engine.begin() as connection:
            connection.execute(
                text("INSERT INTO incidents (id, run_id, organization_id, severity, summary, created_at) VALUES (:id, :run_id, :organization_id, :severity, :summary, :created_at)"),
                {**asdict(incident), "created_at": incident.created_at.isoformat()},
            )

    def list_incidents(self, organization_id: str | None = None) -> list[Incident]:
        query = "SELECT * FROM incidents"
        params: dict[str, Any] = {}
        if organization_id:
            query += " WHERE organization_id = :organization_id"
            params["organization_id"] = organization_id
        query += " ORDER BY created_at DESC"
        rows = self._list(query, params)
        return [Incident(id=row["id"], run_id=row["run_id"], organization_id=row["organization_id"], severity=row["severity"], summary=row["summary"], created_at=datetime.fromisoformat(row["created_at"])) for row in rows]

    def health_snapshot(self) -> dict[str, int | str]:
        with self._connect() as connection:
            return {
                "service": "agent-runtime-control-tower",
                "database_backend": self.engine.url.get_backend_name(),
                "organizations": connection.execute(text("SELECT COUNT(*) FROM organizations")).scalar_one(),
                "agents": connection.execute(text("SELECT COUNT(*) FROM agents")).scalar_one(),
                "mcp_servers": connection.execute(text("SELECT COUNT(*) FROM mcp_servers")).scalar_one(),
                "runs": connection.execute(text("SELECT COUNT(*) FROM agent_runs")).scalar_one(),
                "pending_approvals": connection.execute(text("SELECT COUNT(*) FROM approvals WHERE status = 'pending'")).scalar_one(),
                "incidents": connection.execute(text("SELECT COUNT(*) FROM incidents")).scalar_one(),
            }


SQLiteRepository = ControlTowerRepository
repository = ControlTowerRepository(default_database_url())
