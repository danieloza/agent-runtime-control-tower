from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class OrganizationOut(BaseModel):
    id: str
    name: str
    plan: str


class UserOut(BaseModel):
    id: str
    name: str
    organization_id: str | None
    role: str


class MCPServerOut(BaseModel):
    id: str
    organization_id: str
    name: str
    transport: str
    auth_mode: str
    risk_tier: str


class AgentOut(BaseModel):
    id: str
    organization_id: str
    name: str
    runtime: str
    max_budget_usd: float
    approval_required: bool


class PolicyOut(BaseModel):
    id: str
    organization_id: str
    name: str
    requires_human_approval: bool
    max_tool_calls: int
    deny_sensitive_mcp: bool
    allow_redis_memory: bool


class RunRequestIn(BaseModel):
    agent_id: str
    policy_id: str
    mcp_server_id: str
    task_summary: str = Field(min_length=5, max_length=240)
    estimated_cost_usd: float = Field(ge=0)
    tool_calls_count: int = Field(ge=1, le=100)


class RunOut(BaseModel):
    id: str
    agent_id: str
    organization_id: str
    policy_id: str
    mcp_server_id: str
    requested_by: str
    task_summary: str
    status: str
    risk_reason: str
    tool_calls_count: int
    estimated_cost_usd: float
    approval_id: str | None
    created_at: datetime


class ApprovalOut(BaseModel):
    id: str
    run_id: str
    organization_id: str
    requested_by: str
    reason: str
    status: str
    decided_by: str | None
    created_at: datetime


class ApprovalDecisionIn(BaseModel):
    decision: Literal["approved", "rejected"]


class ReplayRequestIn(BaseModel):
    task_summary_suffix: str | None = Field(default=None, max_length=80)
    override_policy_id: str | None = None
    override_mcp_server_id: str | None = None


class ToolTraceOut(BaseModel):
    id: str
    run_id: str
    tool_name: str
    mcp_server_id: str
    outcome: str
    latency_ms: int


class IncidentOut(BaseModel):
    id: str
    run_id: str
    organization_id: str
    severity: str
    summary: str
    created_at: datetime


class HealthOut(BaseModel):
    service: str
    database_backend: str
    state_backend: str
    organizations: int
    agents: int
    mcp_servers: int
    runs: int
    pending_approvals: int
    incidents: int


class RunStateOut(BaseModel):
    run_id: str
    status: str
    approval_id: str | None = None
    risk_reason: str | None = None
    estimated_cost_usd: float | None = None
    tool_calls_count: int | None = None
    decided_by: str | None = None
    decision: str | None = None
    state_backend: str
