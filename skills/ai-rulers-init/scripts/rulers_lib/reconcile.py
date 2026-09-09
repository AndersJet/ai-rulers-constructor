from __future__ import annotations

import fnmatch
import re
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import AbstractSet, Any, Literal

from .domains import expand_reverse_dependencies


_BASIS = frozenset({"observed", "approved"})
_FACT_HEADERS = ("内容", "依据类型", "证据", "作用域", "置信度")
_UNRESOLVED_HEADERS = ("问题", "重要原因", "作用域", "必需审阅人")
_HEADING_PREFIX = re.compile(
    r"^(?:(?:(?:\d+(?:\.\d+)*|第?[一二三四五六七八九十百]+)(?:[.、章节]|\))?|"
    r"\([0-9一二三四五六七八九十百]+\))\s*)?"
)
_CELL_SPLIT = re.compile(r"(?:<br\s*/?>|[,，])", re.IGNORECASE)


@dataclass(frozen=True)
class EvidenceRecord:
    content: str
    basis: Literal["observed", "approved"]
    evidence: tuple[str, ...]
    scopes: tuple[str, ...]
    confidence: str


@dataclass(frozen=True)
class ProfileSnapshot:
    records: tuple[EvidenceRecord, ...]
    unresolved: tuple[str, ...]


@dataclass(frozen=True)
class ProfileChange:
    kind: Literal["added", "changed", "removed", "evidence_only", "contradicted"]
    before: EvidenceRecord | None
    after: EvidenceRecord | None


def _heading_name(line: str) -> str | None:
    stripped = line.strip()
    if not stripped.startswith("#"):
        return None
    name = stripped.lstrip("#").strip()
    return _HEADING_PREFIX.sub("", name).strip()


def _markdown_cells(line: str) -> tuple[str, ...] | None:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return None
    return tuple(cell.strip() for cell in stripped[1:-1].split("|"))


def _is_separator(cells: Sequence[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)


def _table_rows(
    lines: Sequence[str],
    *,
    section: str,
    headers: tuple[str, ...],
) -> list[tuple[int, tuple[str, ...]]]:
    section_index: int | None = None
    for index, line in enumerate(lines):
        if _heading_name(line) == section:
            section_index = index
            break
    if section_index is None:
        raise ValueError(f"Profile section '{section}' is missing.")

    header_index: int | None = None
    for index in range(section_index + 1, len(lines)):
        if _heading_name(lines[index]) is not None:
            break
        cells = _markdown_cells(lines[index])
        if cells == headers:
            header_index = index
            break
    if header_index is None:
        raise ValueError(
            f"Profile section '{section}' must contain the expected Markdown table."
        )
    separator_index = header_index + 1
    if separator_index >= len(lines):
        raise ValueError(f"Profile line {header_index + 1}: table separator is missing.")
    separator = _markdown_cells(lines[separator_index])
    if separator is None or len(separator) != len(headers) or not _is_separator(separator):
        raise ValueError(
            f"Profile line {separator_index + 1}: invalid Markdown table separator."
        )

    rows: list[tuple[int, tuple[str, ...]]] = []
    for index in range(separator_index + 1, len(lines)):
        if _heading_name(lines[index]) is not None:
            break
        cells = _markdown_cells(lines[index])
        if cells is None:
            if lines[index].strip():
                break
            if rows:
                break
            continue
        if len(cells) != len(headers):
            raise ValueError(
                f"Profile line {index + 1}: expected {len(headers)} table columns, "
                f"got {len(cells)}."
            )
        rows.append((index + 1, cells))
    return rows


def _normalized_text(value: str) -> str:
    return " ".join(value.split())


def _split_values(value: str) -> tuple[str, ...]:
    return tuple(
        sorted({_normalized_text(item) for item in _CELL_SPLIT.split(value) if item.strip()})
    )


def select_profile_sections(text: str, *, scopes: AbstractSet[str], always_sections: Sequence[str]) -> str:
    """Project reviewed Markdown with the same table/scope grammar used by reconcile."""
    lines = text.splitlines()
    row_scopes: dict[int, tuple[str, ...]] = {}
    for section, headers, column in (
        ("当前有效事实与约束", _FACT_HEADERS, 3),
        ("阻塞性未决问题", _UNRESOLVED_HEADERS, 2),
    ):
        for number, cells in _table_rows(lines, section=section, headers=headers):
            row_scopes[number] = _split_values(cells[column])
    sections = set(always_sections) | {"当前有效事实与约束", "阻塞性未决问题"}
    selected = []
    current = None
    for number, line in enumerate(lines, 1):
        heading = _heading_name(line)
        if heading is not None:
            current = heading
        if current not in sections:
            continue
        if number in row_scopes and not (set(row_scopes[number]) & scopes):
            continue
        selected.append(line)
    return "\n".join(selected)


def _record_key(record: EvidenceRecord) -> tuple[str, tuple[str, ...]]:
    return (record.content.casefold(), record.scopes)


def _record_sort_key(record: EvidenceRecord) -> tuple[Any, ...]:
    return (
        record.content.casefold(),
        record.content,
        record.scopes,
        record.basis,
        record.evidence,
        record.confidence,
    )


def parse_profile(
    text: str,
    *,
    allowed_scopes: AbstractSet[str],
) -> ProfileSnapshot:
    allowed = frozenset(allowed_scopes)
    if any(not isinstance(scope, str) or not scope.strip() for scope in allowed):
        raise ValueError("allowed_scopes must contain only non-empty scope names.")
    lines = text.splitlines()
    fact_rows = _table_rows(
        lines,
        section="当前有效事实与约束",
        headers=_FACT_HEADERS,
    )
    records_by_key: dict[tuple[str, tuple[str, ...]], tuple[EvidenceRecord, int]] = {}
    for line_number, cells in fact_rows:
        content = _normalized_text(cells[0])
        if not content:
            raise ValueError(f"Profile line {line_number}: fact content must not be empty.")
        basis = cells[1].strip().casefold()
        if basis not in _BASIS:
            raise ValueError(
                f"Profile line {line_number}: unknown basis '{cells[1]}'; "
                "expected observed or approved."
            )
        evidence = _split_values(cells[2])
        if not evidence:
            raise ValueError(f"Profile line {line_number}: evidence must not be empty.")
        scopes = _split_values(cells[3])
        if not scopes:
            raise ValueError(f"Profile line {line_number}: scope must not be empty.")
        unknown = tuple(scope for scope in scopes if scope not in allowed)
        if unknown:
            raise ValueError(
                f"Profile line {line_number}: unknown scope(s): {', '.join(unknown)}."
            )
        confidence = _normalized_text(cells[4]).casefold()
        record = EvidenceRecord(
            content=content,
            basis=basis,  # type: ignore[arg-type]
            evidence=evidence,
            scopes=scopes,
            confidence=confidence,
        )
        key = _record_key(record)
        previous = records_by_key.get(key)
        if previous is not None and previous[0] != record:
            raise ValueError(
                f"Profile line {line_number}: conflicting duplicate fact; "
                f"the same normalized content and scopes first appeared on line {previous[1]}."
            )
        records_by_key.setdefault(key, (record, line_number))

    unresolved_by_question: dict[str, int] = {}
    unresolved_questions: list[str] = []
    for line_number, cells in _table_rows(
        lines,
        section="阻塞性未决问题",
        headers=_UNRESOLVED_HEADERS,
    ):
        question, reason, raw_scopes, reviewer = (
            _normalized_text(cell) for cell in cells
        )
        for value, field in (
            (question, "question"),
            (reason, "reason"),
            (raw_scopes, "scope"),
            (reviewer, "reviewer"),
        ):
            if not value:
                raise ValueError(
                    f"Profile line {line_number}: unresolved {field} must not be empty."
                )
        scopes = _split_values(raw_scopes)
        unknown = tuple(scope for scope in scopes if scope not in allowed)
        if unknown:
            raise ValueError(
                f"Profile line {line_number}: unresolved scope contains unknown "
                f"value(s): {', '.join(unknown)}."
            )
        normalized_key = question.casefold()
        previous_line = unresolved_by_question.get(normalized_key)
        if previous_line is not None:
            raise ValueError(
                f"Profile line {line_number}: duplicate unresolved question; "
                f"first appeared on line {previous_line}."
            )
        unresolved_by_question[normalized_key] = line_number
        unresolved_questions.append(question)
    unresolved = tuple(
        sorted(
            unresolved_questions,
            key=lambda value: (value.casefold(), value),
        )
    )
    records = tuple(sorted((item[0] for item in records_by_key.values()), key=_record_sort_key))
    return ProfileSnapshot(records=records, unresolved=unresolved)


def _change_sort_key(change: ProfileChange) -> tuple[Any, ...]:
    before = change.before
    after = change.after
    scopes = tuple(sorted(set((before.scopes if before else ()) + (after.scopes if after else ()))))
    return (
        scopes,
        before.content.casefold() if before else "",
        after.content.casefold() if after else "",
        change.kind,
    )


def diff_profiles(
    reviewed: ProfileSnapshot,
    candidate: ProfileSnapshot,
) -> tuple[ProfileChange, ...]:
    before_remaining = set(reviewed.records)
    after_remaining = set(candidate.records)
    changes: list[ProfileChange] = []

    before_by_key = {_record_key(record): record for record in reviewed.records}
    after_by_key = {_record_key(record): record for record in candidate.records}
    for key in sorted(before_by_key.keys() & after_by_key.keys()):
        before = before_by_key[key]
        after = after_by_key[key]
        before_remaining.discard(before)
        after_remaining.discard(after)
        if before != after and before.confidence == after.confidence:
            changes.append(ProfileChange("evidence_only", before, after))
        elif before != after:
            before_remaining.add(before)
            after_remaining.add(after)

    before_by_content: dict[str, list[EvidenceRecord]] = defaultdict(list)
    after_by_content: dict[str, list[EvidenceRecord]] = defaultdict(list)
    for record in before_remaining:
        before_by_content[record.content.casefold()].append(record)
    for record in after_remaining:
        after_by_content[record.content.casefold()].append(record)
    for content in sorted(before_by_content.keys() & after_by_content.keys()):
        before_group = sorted(before_by_content[content], key=_record_sort_key)
        after_group = sorted(after_by_content[content], key=_record_sort_key)
        if len(before_group) == len(after_group) == 1:
            before, after = before_group[0], after_group[0]
            changes.append(ProfileChange("changed", before, after))
            before_remaining.discard(before)
            after_remaining.discard(after)

    before_by_scopes: dict[tuple[str, ...], list[EvidenceRecord]] = defaultdict(list)
    after_by_scopes: dict[tuple[str, ...], list[EvidenceRecord]] = defaultdict(list)
    for record in before_remaining:
        before_by_scopes[record.scopes].append(record)
    for record in after_remaining:
        after_by_scopes[record.scopes].append(record)
    for scopes in sorted(before_by_scopes.keys() & after_by_scopes.keys()):
        before_group = before_by_scopes[scopes]
        after_group = after_by_scopes[scopes]
        if len(before_group) != 1 or len(after_group) != 1:
            continue
        before, after = before_group[0], after_group[0]
        if before.basis == "approved" and after.basis == "observed":
            changes.append(ProfileChange("contradicted", before, after))
            before_remaining.discard(before)
            after_remaining.discard(after)

    changes.extend(ProfileChange("removed", record, None) for record in before_remaining)
    changes.extend(ProfileChange("added", None, record) for record in after_remaining)
    return tuple(sorted(changes, key=_change_sort_key))


def _normalized_path(path: str) -> str | None:
    candidate = PurePosixPath(path.replace("\\", "/"))
    if not path.strip() or candidate.is_absolute() or ".." in candidate.parts:
        return None
    normalized = candidate.as_posix().lstrip("./")
    return normalized if normalized and normalized != "." else None


def _path_matches(path: str, hint: str, *, component_match: bool = False) -> bool:
    normalized_hint = _normalized_path(hint)
    if normalized_hint is None:
        return False
    if path == normalized_hint or path.startswith(normalized_hint.rstrip("/") + "/"):
        return True
    if fnmatch.fnmatchcase(path, normalized_hint) or PurePosixPath(path).match(normalized_hint):
        return True
    if component_match:
        hint_parts = PurePosixPath(normalized_hint).parts
        path_parts = PurePosixPath(path).parts
        width = len(hint_parts)
        return any(path_parts[index : index + width] == hint_parts for index in range(len(path_parts) - width + 1))
    return False


def affected_domains(
    *,
    changes: Sequence[ProfileChange],
    changed_paths: Sequence[str],
    registry: Mapping[str, Mapping[str, Any]],
    index_hints: Mapping[str, Sequence[str]],
) -> frozenset[str]:
    affected: set[str] = set()
    for change in changes:
        if change.kind == "evidence_only":
            continue
        scopes = set(change.before.scopes if change.before else ())
        scopes.update(change.after.scopes if change.after else ())
        if not scopes:
            affected.add("core")
        for scope in scopes:
            affected.add(scope if scope in registry else "core")

    for raw_path in changed_paths:
        path = _normalized_path(raw_path)
        matched: set[str] = set()
        if path is not None:
            for domain in sorted(registry):
                config = registry[domain]
                target_dir = config.get("target_dir")
                if isinstance(target_dir, str) and _path_matches(
                    path, target_dir, component_match=True
                ):
                    matched.add(domain)
                hints = config.get("detection_hints", ())
                if isinstance(hints, Sequence) and not isinstance(hints, (str, bytes)):
                    if any(isinstance(hint, str) and _path_matches(path, hint) for hint in hints):
                        matched.add(domain)
            for domain in sorted(index_hints):
                hints = index_hints[domain]
                if domain not in registry:
                    continue
                if any(isinstance(hint, str) and _path_matches(path, hint) for hint in hints):
                    matched.add(domain)
        affected.update(matched or {"core"})

    return expand_reverse_dependencies(affected, registry)


def domain_actions(
    *,
    state: Mapping[str, Any],
    affected: AbstractSet[str],
    detected: AbstractSet[str],
    retired: AbstractSet[str],
) -> dict[str, Literal["keep", "downgrade", "draft", "retire"]]:
    raw_domains = state.get("domains") or {}
    existing = raw_domains if isinstance(raw_domains, Mapping) else {}
    keys = sorted(set(existing) | set(affected) | set(detected) | set(retired))
    actions: dict[str, Literal["keep", "downgrade", "draft", "retire"]] = {}
    for domain in keys:
        if domain in retired:
            actions[domain] = "retire"
            continue
        if domain not in existing:
            actions[domain] = "draft" if domain in detected else "keep"
            continue
        domain_state = existing[domain]
        review_status = (
            domain_state.get("review_status")
            if isinstance(domain_state, Mapping)
            else None
        )
        reviewed = isinstance(domain_state, Mapping) and (
            isinstance(review_status, str)
            and review_status in {"reviewed", "active"}
            or type(domain_state.get("level")) is int
            and domain_state.get("level", 0) > 0
        )
        actions[domain] = "downgrade" if domain in affected and reviewed else "keep"
    return actions
