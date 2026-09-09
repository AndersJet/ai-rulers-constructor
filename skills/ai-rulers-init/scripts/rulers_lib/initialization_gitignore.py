"""Preserve project ignore rules while keeping local initialization work out of Git."""

from pathlib import Path

WORK_RULE = b"/.rulers-work/"
EQUIVALENT_RULES = {WORK_RULE, b".rulers-work/", b"/.rulers-work", b".rulers-work"}


def check_gitignore_path(root: Path) -> Path:
    path = root / ".gitignore"
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError(
            ".gitignore must be a regular project file; resolve its path before initialization"
        )
    return path


def _may_reinclude_work_directory(line: bytes) -> bool:
    if not line.startswith(b"!"):
        return False
    pattern = line[1:].lstrip(b"/").rstrip(b"/")
    special = b"*?[\\"
    if not any(char in pattern for char in special):
        return pattern == b".rulers-work"
    first = pattern.split(b"/", 1)[0]
    if (
        b"/" in pattern
        and not any(char in first for char in special)
        and first != b".rulers-work"
    ):
        return False
    # Preserve unknown Git glob syntax; a final explicit rule safely wins.
    return True


def with_work_directory_ignored(content: bytes) -> bytes:
    lines = [line.rstrip(b" \t\r") for line in content.split(b"\n")]
    matches = [i for i, line in enumerate(lines) if line in EQUIVALENT_RULES]
    if matches and not any(
        _may_reinclude_work_directory(line) for line in lines[matches[-1] + 1 :]
    ):
        return content
    newline = b"\r\n" if b"\r\n" in content else b"\n"
    separator = b"" if not content or content.endswith(b"\n") else newline
    return content + separator + WORK_RULE + newline


def prepare_gitignore(root: Path) -> None:
    """Only called inside the isolated projection; application uses the reviewed transaction."""
    path = check_gitignore_path(root)
    before = path.read_bytes() if path.exists() else b""
    after = with_work_directory_ignored(before)
    if before != after:
        path.write_bytes(after)
