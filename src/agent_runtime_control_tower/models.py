from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal


RuntimeStatus = Literal["approved", "blocked", "awaiting_approval", "completed"]
IncidentSeverity = Literal["low", "medium", "high"]


@dataclass(slots=True)
class Organization:
    id: str
    name: str
    plan: str


@dataclass(slots=True)
class User:
    id: str
    name: str
    organization_id: str | None
    role: Literal["platform_admin", "security_admin", "operator", "viewer"]
    api_key: str


@dataclass(slots=True)
class MCPServer:
    id: str
    organization_id: str
    name: str
    transport: Literal["stdio", "http"]
    auth_mode: Literal["oauth2", "api_key", "none"]
    risk_tier: Literal["standard", "sensitive", "restricted"]


@dataclass(slots=True)
class Agent:
    id: str
    organization_id: str
    name: str
    runtime: Literal["openai", "custom", "hybrid"]
    max_budget_usd: float
    approval_required: bool


@dataclass(slots=True)
class RuntimePolicy:
    id: str
    organization_id: str
    name: str
    requires_human_approval: bool
    max_tool_calls: int
    deny_sensitive_mcp: bool
    allow_redis_memory: bool


@dataclass(slots=True)
class AgentRun:
    id: str
    agent_id: str
    organization_id: str
    policy_id: str
    mcp_server_id: str
    requested_by: str
    task_summary: str
    status: RuntimeStatus
    risk_reason: str
    tool_calls_count: int
    estimated_cost_usd: float
    approval_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class ApprovalItem:
    id: str
    run_id: str
    organization_id: str
    requested_by: str
    reason: str
    status: Literal["pending", "approved", "rejected"] = "pending"
    decided_by: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class ToolCallTrace:
    id: str
    run_id: str
    tool_name: str
    mcp_server_id: str
    outcome: Literal["allowed", "blocked", "simulated"]
    latency_ms: int


@dataclass(slots=True)
class Incident:
    id: str
    run_id: str
    organization_id: str
    severity: IncidentSeverity
    summary: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
