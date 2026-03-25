# LinkedIn Showcase

## Hook

I built a control tower for AI agents: policy enforcement, human approvals, runtime traces, incidents, PostgreSQL-backed history, and Redis-backed state in one FastAPI service.

## Post

Everyone wants AI agents in production.
Very few teams build the control layer around them.

So I built `Agent Runtime Control Tower`:

- FastAPI control plane for agent execution
- tenant-aware runtime policies
- human approval routing for risky runs
- blocked execution paths with incident creation
- tool call traces for reviewability
- `PostgreSQL` for persistent run history
- `Redis` for fast runtime state
- replay endpoints to validate how a past run behaves under tighter controls

What I wanted to show with this project was not another AI demo, but the missing operational layer around agent systems:

- who is allowed to run what
- which MCP targets are allowed
- when a run should be escalated
- how blocked actions become auditable incidents
- how operators inspect state without relying on model output alone

The demo stack runs with:

- Python
- FastAPI
- SQLAlchemy
- PostgreSQL
- Redis
- Docker Compose

One thing I like most about this project is that it proves three real paths end-to-end:

1. safe run -> approved
2. risky run -> approval required -> approved by admin
3. restricted MCP target -> blocked -> incident created

Repo:
https://github.com/danieloza/agent-runtime-control-tower

If you work on MCP systems, agent infrastructure, or AI platform engineering, I'd be curious what you'd add next: policy DSL, SSO, replay diffing, or budget controls per tenant?

## Short Version

I built a control tower for AI agents with FastAPI, PostgreSQL, Redis, runtime policies, approval routing, execution traces, and incident handling.

The goal was simple: not another AI demo, but the operational layer around agent systems.

This project proves three paths end-to-end:
1. safe run -> approved
2. risky run -> approval required -> approved by admin
3. restricted MCP target -> blocked -> incident created

Repo:
https://github.com/danieloza/agent-runtime-control-tower

## Featured Blurb

FastAPI control tower for AI agents with policy enforcement, approval routing, incident creation, PostgreSQL-backed history, and Redis-backed runtime state.

## Screenshot Plan

1. Dashboard landing screen
Show the visual frame and title so recruiters immediately understand this is an AI control plane, not a toy chatbot.

2. Swagger or `/health` plus live stack proof
Show `database_backend: postgresql` and `state_backend: redis` to prove the system is wired to real infrastructure.

3. Approval plus incident flow
Show one pending approval, one blocked run, and the related trace or incident so the operational story is visible in one glance.
