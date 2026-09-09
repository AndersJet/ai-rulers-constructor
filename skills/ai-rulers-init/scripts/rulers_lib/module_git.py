"""Read-only Git topology adapter. No recursion, fetch, checkout or Git writes."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .module_contracts import checked_path, content_hash, file_identity


def git(root: Path, *args: str, allow_missing=False) -> str:
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True,
                            env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"})
    if result.returncode and not allow_missing:
        raise ValueError(f"Git inspection failed ({args[0]}): {result.stderr.strip()}")
    return result.stdout


def repository_version(root: Path) -> dict:
    top = git(root, "rev-parse", "--show-toplevel").strip()
    if Path(top).resolve() != root.resolve():
        raise ValueError("Module root must be an independent Git worktree")
    return {"head": git(root, "rev-parse", "HEAD").strip(),
            "dirty": bool(git(root, "status", "--porcelain", "--untracked-files=all"))}


def discover_modules(root: Path, *, selected: set[str] | None = None) -> dict:
    top = git(root, "rev-parse", "--show-toplevel").strip()
    if Path(top).resolve() != root:
        raise ValueError("Use the exact main project Git root")
    config = checked_path(root, ".gitmodules")
    if not config.is_file():
        return {"gitmodules_hash": None, "modules": []}
    entries = git(root, "config", "-z", "--file", str(config), "--get-regexp", r"^submodule\..*\.path$", allow_missing=True)
    modules = []
    paths = set()
    for entry in entries.split("\0"):
        if not entry:
            continue
        key, path = entry.split("\n", 1)
        name = key[len("submodule."):-len(".path")]
        if selected is not None and name not in selected:
            continue
        if not name or name in {".", ".."} or len(name.encode("utf-8")) > 120:
            raise ValueError("Unsupported module identity")
        child = checked_path(root, path)
        if path in paths:
            raise ValueError("Multiple modules have the same path")
        paths.add(path)
        tracked = git(root, "ls-files", "--stage", "-z", "--", path)
        rows = [row for row in tracked.split("\0") if row]
        if len(rows) != 1 or rows[0].split("\t", 1)[0].split()[::2] != ["160000", "0"]:
            raise ValueError(f"Module is not a direct, non-conflicted gitlink: {name}")
        recorded = rows[0].split()[1]
        initialized = child.is_dir() and (child / ".git").exists()
        version = repository_version(child) if initialized else {"head": None, "dirty": None}
        url = git(root, "config", "--file", str(config), "--get", f"submodule.{name}.url", allow_missing=True).strip()
        modules.append({"name": name, "path": path, "url_hash": content_hash(url.encode("utf-8")),
                        "recorded_commit": recorded, "initialized": initialized, **version})
    return {"gitmodules_hash": file_identity(config), "modules": sorted(modules, key=lambda m: m["name"])}


def committed_file_identity(root: Path, relative: str) -> str | None:
    result = subprocess.run(["git","-C",str(root),"show",f"HEAD:{relative}"],capture_output=True,
                            env={**os.environ,"GIT_OPTIONAL_LOCKS":"0"})
    return content_hash(result.stdout) if result.returncode == 0 else None
