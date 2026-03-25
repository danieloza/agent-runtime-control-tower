# Architecture

## Goal

Provide a control layer for AI agents in production environments.

The system focuses on questions that sit above the model call:

- is this agent allowed to run?
- can it access this MCP server?
- should this run be blocked or routed to human approval?
- how do we retain a trace of tool usage?
- how do we create incident visibility for unsafe or rejected runs?

## Runtime Flow

1. A tenant-scoped user submits a run request.
2. The system resolves agent, runtime policy, MCP server, and requestor scope.
3. The policy engine evaluates budget, tool call count, MCP risk tier, and approval rules.
4. The run is approved, blocked, or routed to approval.
5. A tool trace is stored for observability.
6. Runtime state is written to Redis or an in-memory fallback for fast operator access.
7. Blocked runs create incident records.
8. Existing runs can be replayed to validate a stricter policy or server choice.

## v2 Platform Upgrades

- `DATABASE_URL`-based repository with SQLAlchemy, allowing local SQLite and production PostgreSQL setups.
- runtime state store abstraction with Redis support and memory fallback.
- replay endpoint for validating how a prior run would behave under a different policy path.
- health reporting that exposes both database and state backends.
