from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


class UnsafeRulersPathError(ValueError):
    pass


_RESERVED_TRANSACTION_NAMES = {
    "maintenance.lock",
    "maintenance.lock.recovery",
}


@dataclass(frozen=True)
class RulersLayout:
    project_root: Path
    rulers_dir: str
    rulers_root: Path

    @property
    def transactions_root(self) -> Path:
        resolved_project = self.project_root.resolve(strict=False)
        resolved_rulers = self.rulers_root.resolve(strict=False)
        if resolved_project != self.project_root or resolved_rulers != self.rulers_root:
            raise UnsafeRulersPathError(
                "Project or rulers root was redirected after layout resolution."
            )
        try:
            resolved_rulers.relative_to(resolved_project)
        except ValueError as exc:
            raise UnsafeRulersPathError(
                "Rulers root escapes the project root."
            ) from exc
        if resolved_rulers == resolved_project:
            raise UnsafeRulersPathError(
                "Rulers root must not be the project root."
            )
        candidate = self.rulers_root / ".transactions"
        if candidate.is_symlink():
            raise UnsafeRulersPathError(
                "Transactions root must not be a symbolic link."
            )
        resolved_candidate = candidate.resolve(strict=False)
        if resolved_candidate.parent != resolved_rulers:
            raise UnsafeRulersPathError(
                "Transactions root escapes the rulers directory."
            )
        return candidate

    @property
    def maintenance_lock_path(self) -> Path:
        return self.transactions_root / "maintenance.lock"

    @property
    def maintenance_recovery_path(self) -> Path:
        return self.transactions_root / "maintenance.lock.recovery"

    def transaction_root(self, transaction_id: str) -> Path:
        relative = Path(transaction_id)
        if (
            not transaction_id.strip()
            or relative == Path(".")
            or relative.parts != (transaction_id,)
        ):
            raise UnsafeRulersPathError(
                f"Transaction ID must be one path component: {transaction_id}"
            )
        if transaction_id in _RESERVED_TRANSACTION_NAMES:
            raise UnsafeRulersPathError(
                f"Transaction ID is reserved by the cold root: {transaction_id}"
            )
        candidate = self.transactions_root / relative
        if candidate.is_symlink() or candidate.resolve(strict=False) != candidate:
            raise UnsafeRulersPathError(
                f"Transaction root must not be redirected: {transaction_id}"
            )
        return candidate


def resolve_safe_child(root: Path, candidate: Path | str) -> Path:
    resolved_root = root.expanduser().resolve()
    relative = Path(candidate)
    if relative.is_absolute() or ".." in relative.parts:
        raise UnsafeRulersPathError(
            f"Path must be relative to its root: {candidate}"
        )
    resolved_candidate = (resolved_root / relative).resolve(strict=False)
    try:
        common = Path(
            os.path.commonpath((str(resolved_root), str(resolved_candidate)))
        )
    except ValueError as exc:
        raise UnsafeRulersPathError(f"Path escapes its root: {candidate}") from exc
    if resolved_candidate == resolved_root or common != resolved_root:
        raise UnsafeRulersPathError(f"Path escapes its root: {candidate}")
    return resolved_candidate


def resolve_layout(project_root: Path | str, rulers_dir: str) -> RulersLayout:
    root = Path(project_root).expanduser().resolve()
    relative = Path(rulers_dir)
    if not rulers_dir.strip() or relative == Path("."):
        raise UnsafeRulersPathError(
            "Rulers directory must not be the project root."
        )
    if relative.is_absolute() or ".." in relative.parts:
        raise UnsafeRulersPathError(
            f"Rulers directory must be a project-relative path: {rulers_dir}"
        )
    try:
        candidate = resolve_safe_child(root, relative)
    except UnsafeRulersPathError as exc:
        raise UnsafeRulersPathError(
            f"Rulers directory escapes project root: {rulers_dir}"
        ) from exc
    return RulersLayout(
        project_root=root,
        rulers_dir=relative.as_posix(),
        rulers_root=candidate,
    )
