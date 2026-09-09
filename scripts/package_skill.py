#!/usr/bin/env python3
"""Reproducible .skill package builder for ai-rulers-init."""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Sequence


FIXED_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
EXCLUDED_DIRS = frozenset({"__pycache__", "evals"})
EXCLUDED_NAMES = frozenset({".DS_Store"})


def collect_skill_files(skill_root: Path) -> list[Path]:
    """Collect all packageable files, sorted for reproducibility."""
    files = []
    for path in sorted(skill_root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(skill_root)
        if any(part in EXCLUDED_DIRS for part in rel.parts):
            continue
        if path.name in EXCLUDED_NAMES:
            continue
        files.append(path)
    root_name = skill_root.name
    files.sort(key=lambda p: f"{root_name}/{p.relative_to(skill_root).as_posix()}")
    return files


def build_skill_package(skill_root: Path, output: Path | None = None) -> Path:
    """Build a reproducible .skill zip package."""
    sys.path.insert(0, str(skill_root / "scripts"))
    from rulers_lib.validation import validate_template

    issues = validate_template(skill_root)
    errors = [i for i in issues if i.severity == "error"]
    if errors:
        raise ValueError(
            "Template validation failed: "
            + "; ".join(f"{e.code} {e.message}" for e in errors)
        )

    if output is None:
        output = skill_root.parent / "ai-rulers-init.skill"

    files = collect_skill_files(skill_root)
    root_name = skill_root.name

    fd, tmp_path = tempfile.mkstemp(
        suffix=".skill.tmp",
        dir=str(output.parent),
    )
    os.close(fd)
    try:
        with zipfile.ZipFile(tmp_path, "w", compression=zipfile.ZIP_STORED) as zf:
            for file_path in files:
                rel = file_path.relative_to(skill_root)
                member = f"{root_name}/{rel.as_posix()}"
                if member.startswith("/") or ".." in member:
                    raise ValueError(f"Unsafe member path: {member}")
                info = zipfile.ZipInfo(member, date_time=FIXED_TIMESTAMP)
                info.compress_type = zipfile.ZIP_STORED
                info.external_attr = 0o644 << 16
                info.create_system = 3
                zf.writestr(info, file_path.read_bytes())
        os.replace(tmp_path, str(output))
    except BaseException:
        try:
            os.unlink(tmp_path)
        except FileNotFoundError:
            pass
        raise
    return output


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build ai-rulers-init .skill package.")
    parser.add_argument("--skill-root", default="skills/ai-rulers-init")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    skill_root = Path(args.skill_root).resolve()
    output = Path(args.output).resolve() if args.output else None
    result = build_skill_package(skill_root, output)
    print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
