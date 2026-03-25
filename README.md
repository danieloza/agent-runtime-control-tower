# Agent Runtime Control Tower v2

> FastAPI control tower for governing AI agents, MCP servers, runtime policies, approvals, replayable runs, and runtime state.

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Control_Tower-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Runtime](https://img.shields.io/badge/AI_Runtime-Governance-12232E?style=for-the-badge)](#)

## Overview

Everyone wants AI agents in production. Very few teams have a control layer for what those agents are allowed to do.

Agent Runtime Control Tower is a backend-first platform primitive for enterprise AI systems. It models the runtime governance layer around agents and MCP servers:

- which agents are allowed to run
- which MCP servers they can access
- when human approval is required
- how risky runs are blocked or escalated
- how tool calls are traced
- how incidents are created for unsafe behavior
- how runtime state can be stored in Redis
- how execution history can be replayed under tighter controls

## What This Project Proves

- Python backend architecture for AI platform primitives
- MCP-aware runtime governance instead of uncontrolled tool access
- deterministic policy enforcement around agent execution
- tenant-aware access control and approval routing
- execution traces and incident visibility for AI operations
- `DATABASE_URL`-driven persistence ready for SQLite or PostgreSQL
- Redis-friendly runtime state for fast operational introspection

## API Surface

- `GET /health`
- `GET /me`
- `GET /organizations`
- `GET /mcp-servers`
- `GET /agents`
- `GET /policies`
- `POST /runs`
- `GET /runs`
- `GET /runs/{run_id}/traces`
- `GET /runs/{run_id}/state`
- `POST /runs/{run_id}/replay`
- `GET /approvals`
- `POST /approvals/{approval_id}/decision`
- `GET /incidents`

## Quickstart

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .
pip install pytest httpx
uvicorn agent_runtime_control_tower.main:app --reload
```

Open:

- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/dashboard`

## Docker Compose Demo

```bash
docker compose up --build
```

This starts:

- API on `http://127.0.0.1:8000`
- PostgreSQL on `localhost:5432`
- Redis on `localhost:6379`

The API container uses:

```text
ART_DATABASE_URL=postgresql+psycopg://postgres:postgres@postgres:5432/agent_runtime_control_tower
ART_REDIS_URL=redis://redis:6379/0
```

## Demo API Keys

- platform admin: `art-admin-demo`
- security admin: `art-security-demo`
- runtime operator: `art-ops-demo`

## v2 Runtime Notes

- persistence is configured via `ART_DATABASE_URL`
- runtime state uses `ART_REDIS_URL` when Redis is available
- if Redis is unavailable, the app falls back to an in-memory state store for local demos and tests

Example PostgreSQL URL:

```text
ART_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/agent_runtime_control_tower
```

## Example Run Request

```powershell
curl -X POST http://127.0.0.1:8000/runs `
  -H "X-API-Key: art-ops-demo" `
  -H "Content-Type: application/json" `
  -d "{\"agent_id\":\"agt_triage\",\"policy_id\":\"pol_ops_default\",\"mcp_server_id\":\"mcp_docs\",\"task_summary\":\"Summarize support issue with KB lookup\",\"estimated_cost_usd\":4.5,\"tool_calls_count\":3}"
```

## Testing

```bash
python -m pip install -e .
python -m pytest -q
```

## Architecture

- runtime API: [main.py](/C:/Users/syfsy/projekty/agent-runtime-control-tower/src/agent_runtime_control_tower/main.py)
- policy engine: [services.py](/C:/Users/syfsy/projekty/agent-runtime-control-tower/src/agent_runtime_control_tower/services.py)
- persistence layer: [repository.py](/C:/Users/syfsy/projekty/agent-runtime-control-tower/src/agent_runtime_control_tower/repository.py)
- architecture notes: [ARCHITECTURE.md](/C:/Users/syfsy/projekty/agent-runtime-control-tower/docs/ARCHITECTURE.md)
- case study: [CASE_STUDY.md](/C:/Users/syfsy/projekty/agent-runtime-control-tower/docs/CASE_STUDY.md)
