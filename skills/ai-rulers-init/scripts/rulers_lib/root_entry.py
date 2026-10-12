from __future__ import annotations

import re


BEGIN = "<!-- ai-rulers-init:begin -->"
END = "<!-- ai-rulers-init:end -->"
SUPPORTED_BLOCK_VERSIONS = frozenset({2, 3})
BLOCK_RE = re.compile(
    r"<!-- ai-rulers-init:begin(?: version=(?P<version>2|3))? -->.*?"
    r"<!-- ai-rulers-init:end -->\n?",
    re.DOTALL,
)
_MARKER_RE = re.compile(
    r"<!--\s*ai-rulers-init:(?P<kind>begin|end)\b[^<>]*-->",
)
_RESERVED_MARKER_PREFIX_RE = re.compile(r"<!--\s*ai-rulers-init:")


class RootEntryConflictError(ValueError):
    pass


def _parse_managed_blocks(text: str) -> tuple[re.Match[str], ...] | None:
    supported_begins = {
        f"<!-- ai-rulers-init:begin version={version} -->"
        for version in SUPPORTED_BLOCK_VERSIONS
    }
    supported_begins.add(BEGIN)
    blocks: list[re.Match[str]] = []
    open_block: int | None = None
    for prefix in _RESERVED_MARKER_PREFIX_RE.finditer(text):
        marker = _MARKER_RE.match(text, prefix.start())
        if marker is None:
            return None
        value = marker.group(0)
        if marker.group("kind") == "begin":
            if value not in supported_begins or open_block is not None:
                return None
            open_block = marker.start()
        else:
            if value != END or open_block is None:
                return None
            block_end = marker.end()
            if text.startswith("\n", block_end):
                block_end += 1
            block = BLOCK_RE.match(text, open_block, block_end)
            if block is None or block.end() != block_end:
                return None
            blocks.append(block)
            open_block = None
    if open_block is not None:
        return None
    return tuple(blocks)


def find_managed_blocks(text: str) -> tuple[re.Match[str], ...]:
    blocks = _parse_managed_blocks(text)
    return () if blocks is None else blocks


def managed_block(rulers_dir: str) -> str:
    return f"""{BEGIN}
## AI Rulers 入口

执行任务前加载 `{rulers_dir}/AGENTS.md`，按其命令读取校验后的 Context。
Context 由 RULERS_STATE.json 派生；blocked 时先诊断，仅加载最低常驻规则。
{END}
"""


def merge_managed_block(existing: str, rulers_dir: str) -> str:
    matches = _parse_managed_blocks(existing)
    if matches is None or len(matches) > 1:
        raise RootEntryConflictError("Malformed or duplicate ai-rulers-init managed blocks.")
    block = managed_block(rulers_dir)
    if matches:
        match = matches[0]
        return existing[: match.start()] + block + existing[match.end() :]
    prefix = existing.rstrip()
    if prefix:
        return prefix + "\n\n" + block
    return block


def has_valid_managed_block(text: str) -> bool:
    matches = _parse_managed_blocks(text)
    return matches is not None and len(matches) == 1
