"""Shared content identities and safe file access for module operations."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .paths import resolve_safe_child


def content_hash(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


def json_bytes(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def identity(value) -> str:
    return content_hash(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def checked_path(root: Path, relative: str, *, required=False) -> Path:
    if not isinstance(relative, str):
        raise ValueError("Module paths must be relative strings")
    candidate = Path(relative)
    if not relative or candidate.is_absolute() or ".." in candidate.parts or ".git" in candidate.parts:
        raise ValueError(f"Unsafe module path: {relative}")
    lexical = root / candidate
    resolved = resolve_safe_child(root, candidate)
    if lexical != resolved or lexical.is_symlink():
        raise ValueError(f"Module path must not be redirected: {relative}")
    if required and not resolved.is_file():
        raise ValueError(f"Required module input is unavailable: {relative}")
    return resolved


def read_json(path: Path):
    if path.is_symlink():
        raise ValueError("JSON input must not be a symbolic link")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Module JSON input must be an object")
    return value


def file_identity(path: Path) -> str | None:
    return content_hash(path.read_bytes()) if path.is_file() else None


def write_plan(path: Path, plan: dict, *, root: Path) -> None:
    relative = path.relative_to(root).as_posix() if path.is_absolute() else path.as_posix()
    target = checked_path(root, relative)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if target.read_bytes() == json_bytes(plan):
            return
        raise ValueError("Plan output exists; choose a new path")
    with target.open("xb") as stream:
        stream.write(json_bytes(plan))


def engine_identity() -> str:
    root = Path(__file__).resolve().parent
    return identity({path.name:file_identity(path) for path in sorted(root.glob("*.py"))})


MODULE_PLAN_SCHEMA_VERSION = 1
EXPORT_SCHEMA_VERSION = 1
EXPORT_MANIFEST_SCHEMA_VERSION = 1


def require_protocol(value: dict, field: str, expected: int) -> None:
    actual = value.get(field)
    if type(actual) is not int or actual != expected:
        raise ValueError(f"Unsupported {field}: {actual!r}; expected {expected}. Use a compatible Skill or regenerate the input.")
