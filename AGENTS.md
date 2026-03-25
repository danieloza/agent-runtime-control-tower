# AGENTS.md

## Project Mission

Build a backend-first control plane that governs automation and AI workflow execution with deterministic approval rules, usage limits, and auditability.

## Engineering Rules

- Keep business rules deterministic and easy to explain.
- Prefer simple, explicit services over premature abstractions.
- Treat workflow execution policy as product logic, not infrastructure trivia.
- Avoid adding AI into decision-making paths that should stay auditable.

## Current MVP Scope

- organizations
- workflows
- plan restrictions
- approval queue
- execution decisions
- usage counters

## Near-term Priorities

1. Replace in-memory storage with a persistent database.
2. Add auth and tenant-aware access control.
3. Add a small admin dashboard for approvals and logs.
