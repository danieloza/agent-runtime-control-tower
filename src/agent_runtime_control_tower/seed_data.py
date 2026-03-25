from __future__ import annotations

from agent_runtime_control_tower.models import Agent, MCPServer, Organization, RuntimePolicy, User


SEED_ORGANIZATIONS = [
    Organization(id="org_acme", name="ACME AI Platform", plan="growth"),
    Organization(id="org_nova", name="Nova Internal Tools", plan="enterprise"),
]

SEED_USERS = [
    User(id="usr_platform_admin", name="Platform Admin", organization_id=None, role="platform_admin", api_key="art-admin-demo"),
    User(id="usr_security_admin", name="Security Admin", organization_id="org_nova", role="security_admin", api_key="art-security-demo"),
    User(id="usr_operator", name="Runtime Operator", organization_id="org_acme", role="operator", api_key="art-ops-demo"),
]

SEED_MCP_SERVERS = [
    MCPServer(id="mcp_docs", organization_id="org_acme", name="Internal Docs MCP", transport="http", auth_mode="oauth2", risk_tier="standard"),
    MCPServer(id="mcp_finance", organization_id="org_nova", name="Finance Systems MCP", transport="stdio", auth_mode="oauth2", risk_tier="restricted"),
]

SEED_AGENTS = [
    Agent(id="agt_triage", organization_id="org_acme", name="Support Triage Agent", runtime="hybrid", max_budget_usd=15.0, approval_required=False),
    Agent(id="agt_finops", organization_id="org_nova", name="FinOps Review Agent", runtime="openai", max_budget_usd=40.0, approval_required=True),
]

SEED_POLICIES = [
    RuntimePolicy(id="pol_ops_default", organization_id="org_acme", name="Operator Default Policy", requires_human_approval=False, max_tool_calls=8, deny_sensitive_mcp=True, allow_redis_memory=True),
    RuntimePolicy(id="pol_finance_guarded", organization_id="org_nova", name="Finance Guarded Policy", requires_human_approval=True, max_tool_calls=5, deny_sensitive_mcp=False, allow_redis_memory=True),
]
