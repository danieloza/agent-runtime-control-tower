from __future__ import annotations

import json
from typing import Protocol

from redis import Redis
from redis.exceptions import RedisError


class RuntimeStateStore(Protocol):
    backend_name: str

    def upsert_run_state(self, run_id: str, payload: dict[str, str | int | float | bool | None]) -> None: ...

    def get_run_state(self, run_id: str) -> dict[str, str | int | float | bool | None] | None: ...


class InMemoryRuntimeStateStore:
    backend_name = "memory"

    def __init__(self) -> None:
        self._runs: dict[str, dict[str, str | int | float | bool | None]] = {}

    def upsert_run_state(self, run_id: str, payload: dict[str, str | int | float | bool | None]) -> None:
        self._runs[run_id] = payload

    def get_run_state(self, run_id: str) -> dict[str, str | int | float | bool | None] | None:
        return self._runs.get(run_id)


class RedisRuntimeStateStore:
    backend_name = "redis"

    def __init__(self, url: str) -> None:
        self.client = Redis.from_url(url, decode_responses=True)
        self.client.ping()

    def upsert_run_state(self, run_id: str, payload: dict[str, str | int | float | bool | None]) -> None:
        self.client.set(f"run:{run_id}", json.dumps(payload))

    def get_run_state(self, run_id: str) -> dict[str, str | int | float | bool | None] | None:
        raw = self.client.get(f"run:{run_id}")
        return json.loads(raw) if raw else None


def build_runtime_state_store(url: str | None) -> RuntimeStateStore:
    if not url:
        return InMemoryRuntimeStateStore()
    try:
        return RedisRuntimeStateStore(url)
    except RedisError:
        return InMemoryRuntimeStateStore()
