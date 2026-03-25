from __future__ import annotations

import os
from pathlib import Path


def default_database_url() -> str:
    configured = os.environ.get("ART_DATABASE_URL")
    if configured:
        return configured
    default_path = Path(__file__).resolve().parents[2] / "data" / "runtime_tower.db"
    return f"sqlite:///{default_path}"


def redis_url() -> str | None:
    return os.environ.get("ART_REDIS_URL")
