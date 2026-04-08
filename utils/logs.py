from __future__ import annotations

from datetime import datetime, timezone


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _emit(level: str, message: str) -> None:
    print(f"[{_timestamp()}] [{level}] {message}", flush=True)


def section(title: str) -> None:
    line = "=" * 72
    print(line, flush=True)
    _emit("SECTION", title)
    print(line, flush=True)


def info(message: str) -> None:
    _emit("INFO", message)


def success(message: str) -> None:
    _emit("SUCCESS", message)


def warning(message: str) -> None:
    _emit("WARNING", message)


def error(message: str) -> None:
    _emit("ERROR", message)
