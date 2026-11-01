"""Backend package for patient-flow decision support MVP."""

from __future__ import annotations

import os
from pathlib import Path


def _strip_env_value(raw: str) -> str:
    value = raw.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _load_project_env() -> None:
    """Load a local .env file when the backend process starts.

    This keeps local FastAPI runs consistent even when the IDE/debug runner does
    not export shell variables into the backend worker process.
    """
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return

    try:
        raw_text = env_path.read_text(encoding="utf-8")
    except OSError:
        return

    lines = [line.strip() for line in raw_text.splitlines() if line.strip() and not line.strip().startswith("#")]

    # Tolerate a raw single-line key in .env for local development.
    if len(lines) == 1 and "=" not in lines[0] and lines[0].startswith("sk-") and not os.getenv("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = lines[0]
        return

    for line in lines:
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        os.environ.setdefault(key, _strip_env_value(value))

    # Accept common local naming mistakes without breaking the canonical name.
    if not os.getenv("OPENAI_API_KEY"):
        fallback_key = os.getenv("OPEN_API_KEY") or os.getenv("OPEN_AI_API_KEY")
        if fallback_key:
            os.environ["OPENAI_API_KEY"] = fallback_key

    if not os.getenv("ENABLE_OPENAI_REALTIME"):
        fallback_realtime = os.getenv("ENABLE_REALTIME")
        if fallback_realtime:
            os.environ["ENABLE_OPENAI_REALTIME"] = fallback_realtime


_load_project_env()
