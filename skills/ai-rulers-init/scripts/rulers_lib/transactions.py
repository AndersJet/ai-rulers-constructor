from __future__ import annotations

import errno
import fcntl
import hashlib
import json
import os
import shutil
import stat
import tempfile
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

from .paths import RulersLayout, UnsafeRulersPathError, resolve_safe_child
from .state import state_json


_SINGLE_STATE_PLAN_ID = "single-state-writer"
_JOURNAL_NAME = "journal.json"
_SNAPSHOTS_DIR = "snapshots"
_HASH_PREFIX = "sha256:"
_JOURNAL_PHASES = {
    "prepared",
    "applying",
    "committing",
    "rolling_back",
}
_ACTION_PHASES = {"prepared", "applied"}


class TransactionError(RuntimeError):
    pass


@dataclass(frozen=True)
class ReplaceAction:
    path: str
    content: bytes


@dataclass(frozen=True)
class DeleteAction:
    path: str


FileAction = ReplaceAction | DeleteAction


@dataclass(frozen=True)
class InspectedTransactionAction:
    index: int
    path: str
    kind: str
    original_sha256: str | None
    snapshot_ref: str | None
    snapshot_sha256: str | None
    original_existed: bool
    phase: str


@dataclass(frozen=True)
class InspectedTransaction:
    transaction_id: str
    actions: tuple[InspectedTransactionAction, ...]
    lock_path: str
    lock_sha256: str
    lock_nonce: str
    journal_path: str | None
    journal_sha256: str | None
    requires_replan: bool


@dataclass(frozen=True)
class TransactionArtifactFact:
    role: str
    path: str
    sha256: str


@dataclass(frozen=True)
class TransactionSnapshot:
    incomplete_present: bool
    artifacts: tuple[TransactionArtifactFact, ...]
    transaction_id: str | None
    lock_nonce: str | None
    actions: tuple[InspectedTransactionAction, ...]
    requires_replan: bool
    semantic_error: str | None


@dataclass
class _LockLease:
    path: Path
    nonce: str
    release_on_exit: bool = True

    def retain(self) -> None:
        self.release_on_exit = False


@dataclass(frozen=True)
class _PreparedAction:
    relative: str
    kind: str
    content: bytes | None
    journal_index: int


def _sha256(content: bytes) -> str:
    return _HASH_PREFIX + hashlib.sha256(content).hexdigest()


def _lexists(path: Path) -> bool:
    return os.path.lexists(path)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_exclusive(path: Path, content: bytes, *, mode: int = 0o600) -> None:
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, mode)
    try:
        os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    _fsync_directory(path.parent)


def _atomic_replace_bytes(
    path: Path,
    content: bytes,
    *,
    target_mode: int | None = None,
) -> bool:
    if not isinstance(content, bytes):
        raise TypeError("atomic replacement content must be bytes")
    if path.exists():
        if not path.is_file():
            raise TransactionError(f"Atomic replacement target is not a file: {path}")
        if path.read_bytes() == content:
            if target_mode is None or stat.S_IMODE(path.stat().st_mode) == target_mode:
                return False
            path.chmod(target_mode)
            with path.open("rb") as stream:
                os.fsync(stream.fileno())
            _fsync_directory(path.parent)
            return True

    parent = path.parent
    if not parent.is_dir():
        raise TransactionError(f"Atomic replacement parent does not exist: {parent}")

    replacement_mode = target_mode
    if replacement_mode is None:
        replacement_mode = (
            stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o644
        )
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=parent,
    )
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, replacement_mode)
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        _fsync_directory(parent)
        return True
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def atomic_replace_bytes(path: Path, content: bytes) -> bool:
    return _atomic_replace_bytes(path, content)


def write_state_atomic(path: Path, state: Mapping[str, Any]) -> bool:
    content = state_json(dict(state)).encode("utf-8")
    return atomic_replace_bytes(path, content)


def _json_bytes(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _read_lock(path: Path) -> tuple[dict[str, Any], bytes]:
    if path.is_symlink() or not path.is_file():
        raise TransactionError(f"Maintenance lock is not a regular file: {path}")
    try:
        content = path.read_bytes()
    except OSError as exc:
        raise TransactionError(f"Maintenance lock is unreadable: {path}") from exc
    return _decode_lock(content, path), content


def _decode_lock(content: bytes, path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TransactionError(f"Maintenance lock is unreadable: {path}") from exc
    if not isinstance(payload, dict) or set(payload) != {"plan_id", "pid", "nonce"}:
        raise TransactionError(f"Maintenance lock has an invalid shape: {path}")
    if not isinstance(payload["plan_id"], str) or not payload["plan_id"]:
        raise TransactionError(f"Maintenance lock has an invalid plan ID: {path}")
    if (
        not isinstance(payload["pid"], int)
        or isinstance(payload["pid"], bool)
        or payload["pid"] <= 0
    ):
        raise TransactionError(f"Maintenance lock has an invalid PID: {path}")
    if not isinstance(payload["nonce"], str) or not payload["nonce"]:
        raise TransactionError(f"Maintenance lock has an invalid nonce: {path}")
    return payload


def _pid_is_active(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError as exc:
        if exc.errno == errno.ESRCH:
            return False
        if exc.errno == errno.EPERM:
            return True
        raise TransactionError(f"Could not inspect maintenance lock PID {pid}") from exc
    return True


def _remove_owned_lock(lease: _LockLease) -> None:
    if not _lexists(lease.path):
        return
    payload, _ = _read_lock(lease.path)
    if payload["nonce"] != lease.nonce:
        raise TransactionError("Maintenance lock ownership changed before release")
    lease.path.unlink()
    _fsync_directory(lease.path.parent)


def _acquire_recovery_lease(
    *,
    cold_root: Path,
    lock_path: Path,
    plan_id: str,
) -> _LockLease:
    nonce = uuid.uuid4().hex
    content = _json_bytes({"plan_id": plan_id, "pid": os.getpid(), "nonce": nonce})
    if not _lexists(lock_path):
        try:
            _write_exclusive(lock_path, content)
        except FileExistsError as exc:
            raise TransactionError("Another recovery acquired the lease") from exc
        return _LockLease(lock_path, nonce)

    payload, _ = _read_lock(lock_path)
    if payload["plan_id"] != plan_id:
        raise TransactionError("Recovery lease belongs to another transaction")
    if _pid_is_active(payload["pid"]):
        raise TransactionError("An active recovery holds the lease")

    descriptor = -1
    try:
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(lock_path, flags)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise TransactionError("Another recovery is reclaiming the lease") from exc
        opened = os.fstat(descriptor)
        current = os.lstat(lock_path)
        if (opened.st_dev, opened.st_ino) != (current.st_dev, current.st_ino):
            raise TransactionError("Recovery lease changed during reclaim")
        refreshed, _ = _read_lock(lock_path)
        if refreshed["plan_id"] != plan_id:
            raise TransactionError("Recovery lease changed transaction ownership")
        if _pid_is_active(refreshed["pid"]):
            raise TransactionError("An active recovery holds the lease")
        lock_path.unlink()
        _fsync_directory(cold_root)
        try:
            _write_exclusive(lock_path, content)
        except FileExistsError as exc:
            raise TransactionError("Another recovery acquired the lease") from exc
        return _LockLease(lock_path, nonce)
    except OSError as exc:
        raise TransactionError("Could not safely reclaim the recovery lease") from exc
    finally:
        if descriptor >= 0:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            finally:
                os.close(descriptor)


def _transaction_paths(layout: RulersLayout) -> tuple[Path, Path, Path]:
    try:
        cold_root = layout.transactions_root
    except UnsafeRulersPathError as exc:
        raise TransactionError("Unsafe transactions root") from exc
    return (
        cold_root,
        cold_root / "maintenance.lock",
        cold_root / "maintenance.lock.recovery",
    )


def _cold_transaction_entries(
    cold_root: Path,
    lock_path: Path,
    recovery_path: Path,
) -> list[Path]:
    return sorted(
        entry
        for entry in cold_root.iterdir()
        if entry not in {lock_path, recovery_path}
    )


@contextmanager
def _acquire_maintenance_lock(
    *,
    layout: RulersLayout,
    plan_id: str,
) -> Iterator[_LockLease]:
    cold_root, lock_path, recovery_path = _transaction_paths(layout)
    try:
        cold_root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise TransactionError("Transactions root is not a usable directory") from exc
    _fsync_directory(cold_root.parent)
    cold_root, lock_path, recovery_path = _transaction_paths(layout)
    if _lexists(recovery_path):
        raise TransactionError("Transaction recovery is already in progress")
    if _cold_transaction_entries(cold_root, lock_path, recovery_path):
        raise TransactionError("An incomplete transaction blocks maintenance")

    nonce = uuid.uuid4().hex
    payload = {"plan_id": plan_id, "pid": os.getpid(), "nonce": nonce}
    try:
        _write_exclusive(lock_path, _json_bytes(payload))
    except FileExistsError as exc:
        raise TransactionError("Another maintenance writer holds the lock") from exc

    lease = _LockLease(lock_path, nonce)
    if _lexists(recovery_path):
        _remove_owned_lock(lease)
        raise TransactionError("Transaction recovery is already in progress")
    try:
        yield lease
    finally:
        if lease.release_on_exit:
            _remove_owned_lock(lease)


@contextmanager
def maintenance_lock(*, layout: RulersLayout) -> Iterator[None]:
    with _acquire_maintenance_lock(
        layout=layout,
        plan_id=_SINGLE_STATE_PLAN_ID,
    ):
        yield


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _reject_symlink_components(root: Path, relative: Path) -> None:
    current = root
    for component in relative.parts:
        current = current / component
        if current.is_symlink():
            raise TransactionError(f"Transaction target contains a symlink: {relative}")


def _validate_target(
    layout: RulersLayout,
    candidate: Path | str,
    *,
    restore_original: bool = False,
) -> tuple[Path, str]:
    relative = Path(candidate)
    if relative.is_absolute() or ".." in relative.parts or relative == Path("."):
        raise TransactionError(f"Transaction target must be project-relative: {candidate}")
    _reject_symlink_components(layout.project_root, relative)
    try:
        target = resolve_safe_child(layout.project_root, relative)
    except UnsafeRulersPathError as exc:
        raise TransactionError(f"Unsafe transaction target: {candidate}") from exc

    project_relative = target.relative_to(layout.project_root).as_posix()
    rulers_root = layout.rulers_root.resolve(strict=False)
    cold_roots = (
        (layout.rulers_root / ".plans").resolve(strict=False),
        layout.transactions_root.resolve(strict=False),
    )
    allowed = False
    if _is_within(target, rulers_root) and target != rulers_root:
        allowed = not any(_is_within(target, cold_root) for cold_root in cold_roots)
    elif target in {layout.project_root / "AGENTS.md", layout.project_root / "CHANGELOG.md", layout.project_root / ".gitignore"}:
        allowed = True
    elif target == layout.project_root / "CLAUDE.md":
        allowed = target.is_file() or (restore_original and not target.exists())
    elif target == layout.project_root / "CHANGELOG.md":
        allowed = target.is_file() or (restore_original and not target.exists())
    if not allowed:
        raise TransactionError(f"Transaction target is outside the allowlist: {candidate}")
    if target.exists() and not target.is_file():
        raise TransactionError(f"Transaction target is not a file: {candidate}")
    return target, project_relative


def validate_transaction_target(
    layout: RulersLayout,
    candidate: Path | str,
    *,
    restore_original: bool = False,
) -> tuple[Path, str]:
    """Validate one target against the transaction writer's sole allowlist."""
    return _validate_target(
        layout,
        candidate,
        restore_original=restore_original,
    )


def _empty_journal(transaction_id: str, lock_nonce: str) -> dict[str, Any]:
    return {
        "transaction_id": transaction_id,
        "lock_nonce": lock_nonce,
        "phase": "prepared",
        "actions": [],
    }


def _resolve_transaction_artifact(
    transaction_root: Path,
    relative: Path | str,
) -> Path:
    artifact_relative = Path(relative)
    if transaction_root.is_symlink() or not transaction_root.is_dir():
        raise TransactionError("Transaction root is missing or redirected")
    if transaction_root.resolve(strict=False) != transaction_root:
        raise TransactionError("Transaction root escapes the cold root")
    current = transaction_root
    for component in artifact_relative.parts:
        current = current / component
        if current.is_symlink():
            raise TransactionError(
                f"Transaction artifact must not be a symbolic link: {relative}"
            )
    try:
        resolved = resolve_safe_child(transaction_root, artifact_relative)
    except UnsafeRulersPathError as exc:
        raise TransactionError("Transaction artifact reference escapes") from exc
    if resolved != current:
        raise TransactionError("Transaction artifact path was redirected")
    return current


def _write_journal(transaction_root: Path, journal: Mapping[str, Any]) -> None:
    path = _resolve_transaction_artifact(transaction_root, _JOURNAL_NAME)
    atomic_replace_bytes(path, _json_bytes(journal))


def _load_journal(transaction_root: Path) -> dict[str, Any]:
    path = _resolve_transaction_artifact(transaction_root, _JOURNAL_NAME)
    try:
        content = path.read_bytes()
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TransactionError(f"Transaction journal is unreadable: {path}") from exc
    return _decode_journal(content, path)


def _decode_journal(content: bytes, path: Path) -> dict[str, Any]:
    try:
        value = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TransactionError(f"Transaction journal is unreadable: {path}") from exc
    if not isinstance(value, dict):
        raise TransactionError(f"Transaction journal has an invalid shape: {path}")
    return value


def _validate_journal(
    *,
    layout: RulersLayout,
    transaction_root: Path,
    journal: Mapping[str, Any],
    transaction_id: str,
    lock_nonce: str,
) -> list[tuple[dict[str, Any], bytes | None]]:
    if set(journal) != {"transaction_id", "lock_nonce", "phase", "actions"}:
        raise TransactionError("Transaction journal contains unsupported fields")
    if journal["transaction_id"] != transaction_id:
        raise TransactionError("Transaction journal ID does not match the lock")
    if journal["lock_nonce"] != lock_nonce:
        raise TransactionError("Transaction journal lock nonce does not match")
    if (
        not isinstance(journal["phase"], str)
        or journal["phase"] not in _JOURNAL_PHASES
    ):
        raise TransactionError("Transaction journal has an invalid phase")
    actions = journal["actions"]
    if not isinstance(actions, list):
        raise TransactionError("Transaction journal actions must be a list")

    validated: list[tuple[dict[str, Any], bytes | None]] = []
    seen_snapshot_refs: set[str] = set()
    seen_targets: set[str] = set()
    action_fields = {
        "path",
        "kind",
        "original_sha256",
        "snapshot_ref",
        "snapshot_sha256",
        "original_existed",
        "phase",
    }
    for index, entry in enumerate(actions):
        if not isinstance(entry, dict) or set(entry) != action_fields:
            raise TransactionError("Transaction journal action has an invalid shape")
        if (
            not isinstance(entry["kind"], str)
            or entry["kind"] not in {"replace", "delete"}
        ):
            raise TransactionError("Transaction journal action has an invalid kind")
        if (
            not isinstance(entry["phase"], str)
            or entry["phase"] not in _ACTION_PHASES
        ):
            raise TransactionError("Transaction journal action has an invalid phase")
        if not isinstance(entry["path"], str):
            raise TransactionError("Transaction journal action path must be text")
        if not isinstance(entry["original_existed"], bool):
            raise TransactionError("Transaction journal existence flag is invalid")
        _, canonical_relative = _validate_target(
            layout,
            entry["path"],
            restore_original=entry["original_existed"],
        )
        if canonical_relative != entry["path"]:
            raise TransactionError("Transaction journal path is not canonical")
        if canonical_relative in seen_targets:
            raise TransactionError(
                f"Duplicate transaction target: {canonical_relative}"
            )
        seen_targets.add(canonical_relative)

        snapshot_content: bytes | None = None
        if entry["original_existed"]:
            snapshot_ref = entry["snapshot_ref"]
            snapshot_sha256 = entry["snapshot_sha256"]
            original_sha256 = entry["original_sha256"]
            if not all(
                isinstance(value, str)
                for value in (snapshot_ref, snapshot_sha256, original_sha256)
            ):
                raise TransactionError("Transaction snapshot metadata is incomplete")
            expected_snapshot_ref = f"{_SNAPSHOTS_DIR}/{index:06d}.bin"
            if snapshot_ref != expected_snapshot_ref:
                raise TransactionError(
                    "Transaction snapshot reference does not match its action index"
                )
            if snapshot_ref in seen_snapshot_refs:
                raise TransactionError("Transaction snapshot reference is duplicated")
            seen_snapshot_refs.add(snapshot_ref)
            snapshot_relative = Path(snapshot_ref)
            if (
                snapshot_relative.is_absolute()
                or ".." in snapshot_relative.parts
                or not snapshot_relative.parts
                or snapshot_relative.parts[0] != _SNAPSHOTS_DIR
                or len(snapshot_relative.parts) < 2
            ):
                raise TransactionError("Transaction snapshot reference is unsafe")
            snapshot_path = _resolve_transaction_artifact(
                transaction_root,
                snapshot_relative,
            )
            try:
                snapshot_content = snapshot_path.read_bytes()
            except OSError as exc:
                raise TransactionError("Transaction snapshot cannot be read") from exc
            actual_hash = _sha256(snapshot_content)
            if actual_hash != snapshot_sha256 or actual_hash != original_sha256:
                raise TransactionError("Transaction snapshot hash does not match journal")
        elif any(
            entry[field] is not None
            for field in ("original_sha256", "snapshot_ref", "snapshot_sha256")
        ):
            raise TransactionError("Absent original file must not have a snapshot")
        validated.append((entry, snapshot_content))
    return validated


def _atomic_remove(path: Path) -> bool:
    try:
        path.unlink()
    except FileNotFoundError:
        return False
    _fsync_directory(path.parent)
    return True


def _restore_from_journal(
    *,
    layout: RulersLayout,
    transaction_root: Path,
    journal: Mapping[str, Any],
    transaction_id: str,
    lock_nonce: str,
) -> tuple[str, ...]:
    validated = _validate_journal(
        layout=layout,
        transaction_root=transaction_root,
        journal=journal,
        transaction_id=transaction_id,
        lock_nonce=lock_nonce,
    )
    changed: set[str] = set()
    for entry, snapshot_content in reversed(validated):
        target, relative = _validate_target(
            layout,
            entry["path"],
            restore_original=entry["original_existed"],
        )
        if entry["original_existed"]:
            snapshot_ref = entry["snapshot_ref"]
            snapshot_path = _resolve_transaction_artifact(
                transaction_root,
                snapshot_ref,
            )
            current_snapshot = snapshot_path.read_bytes()
            if (
                _sha256(current_snapshot) != entry["snapshot_sha256"]
                or current_snapshot != snapshot_content
            ):
                raise TransactionError("Transaction snapshot changed during restore")
            snapshot_mode = stat.S_IMODE(snapshot_path.stat().st_mode)
            if _atomic_replace_bytes(
                target,
                current_snapshot,
                target_mode=snapshot_mode,
            ):
                changed.add(relative)
        elif _atomic_remove(target):
            changed.add(relative)
    return tuple(sorted(changed))


class FileTransaction:
    def __init__(
        self,
        *,
        layout: RulersLayout,
        plan_id: str,
        transaction_root: Path,
        lock_nonce: str,
    ) -> None:
        self._layout = layout
        self._plan_id = plan_id
        self._transaction_root = transaction_root
        self._lock_nonce = lock_nonce
        self._journal = _empty_journal(plan_id, lock_nonce)
        self._closed = False
        self._owns_transaction_root = False
        self._seen_targets: set[str] = set()

    def _initialize(self) -> None:
        cold_root, _, _ = _transaction_paths(self._layout)
        if self._transaction_root.parent != cold_root:
            raise TransactionError("Transaction root moved outside the cold root")
        self._transaction_root.mkdir(parents=False, exist_ok=False)
        self._owns_transaction_root = True
        try:
            snapshots = self._transaction_root / _SNAPSHOTS_DIR
            snapshots.mkdir()
            _fsync_directory(self._transaction_root)
            _fsync_directory(self._transaction_root.parent)
            _write_exclusive(
                self._transaction_root / _JOURNAL_NAME,
                _json_bytes(self._journal),
            )
        except BaseException:
            shutil.rmtree(self._transaction_root)
            _fsync_directory(self._transaction_root.parent)
            self._owns_transaction_root = False
            raise

    def _prepare(self, actions: Sequence[FileAction]) -> list[_PreparedAction]:
        if self._closed:
            raise TransactionError("Transaction is already closed")
        pending: list[tuple[Path, str, str, bytes | None, bytes | None]] = []
        seen = set(self._seen_targets)
        for action in actions:
            if isinstance(action, ReplaceAction):
                if not isinstance(action.content, bytes):
                    raise TypeError("replacement content must be bytes")
                target, relative = _validate_target(self._layout, action.path)
                if relative in seen:
                    raise TransactionError(f"Duplicate transaction target: {relative}")
                seen.add(relative)
                original = target.read_bytes() if target.exists() else None
                if original == action.content:
                    continue
                pending.append((target, relative, "replace", action.content, original))
            elif isinstance(action, DeleteAction):
                target, relative = _validate_target(self._layout, action.path)
                if relative in seen:
                    raise TransactionError(f"Duplicate transaction target: {relative}")
                seen.add(relative)
                if not target.exists():
                    continue
                pending.append((target, relative, "delete", None, target.read_bytes()))
            else:
                raise TypeError(f"Unsupported file action: {type(action).__name__}")

        prepared: list[_PreparedAction] = []
        entries: list[dict[str, Any]] = []
        snapshots_root = self._transaction_root / _SNAPSHOTS_DIR
        start_index = len(self._journal["actions"])
        for offset, (target, relative, kind, content, original) in enumerate(pending):
            journal_index = start_index + offset
            snapshot_ref: str | None = None
            original_hash: str | None = None
            if original is not None:
                snapshot_ref = f"{_SNAPSHOTS_DIR}/{journal_index:06d}.bin"
                original_hash = _sha256(original)
                snapshot_path = _resolve_transaction_artifact(
                    self._transaction_root,
                    snapshot_ref,
                )
                _write_exclusive(
                    snapshot_path,
                    original,
                    mode=stat.S_IMODE(target.stat().st_mode),
                )
            entries.append(
                {
                    "path": relative,
                    "kind": kind,
                    "original_sha256": original_hash,
                    "snapshot_ref": snapshot_ref,
                    "snapshot_sha256": original_hash,
                    "original_existed": original is not None,
                    "phase": "prepared",
                }
            )
            prepared.append(_PreparedAction(relative, kind, content, journal_index))
        if entries:
            _fsync_directory(snapshots_root)
            self._journal["actions"].extend(entries)
            self._journal["phase"] = "prepared"
            _write_journal(self._transaction_root, self._journal)
            self._seen_targets.update(entry["path"] for entry in entries)
        return prepared

    def replace_bytes(self, path: Path, content: bytes) -> bool:
        return bool(self.apply([ReplaceAction(path.as_posix(), content)]))

    def remove(self, path: Path) -> bool:
        return bool(self.apply([DeleteAction(path.as_posix())]))

    def apply(self, actions: Sequence[FileAction]) -> tuple[str, ...]:
        prepared = self._prepare(actions)
        if not prepared:
            return ()
        self._journal["phase"] = "applying"
        _write_journal(self._transaction_root, self._journal)
        changed: list[str] = []
        for action in prepared:
            target, _ = _validate_target(self._layout, action.relative)
            if action.kind == "replace":
                assert action.content is not None
                target.parent.mkdir(parents=True, exist_ok=True)
                did_change = atomic_replace_bytes(target, action.content)
            else:
                did_change = _atomic_remove(target)
            self._journal["actions"][action.journal_index]["phase"] = "applied"
            _write_journal(self._transaction_root, self._journal)
            if did_change:
                changed.append(action.relative)
        return tuple(changed)

    def commit(self) -> None:
        if self._closed:
            return
        self._journal["phase"] = "committing"
        _write_journal(self._transaction_root, self._journal)
        shutil.rmtree(self._transaction_root)
        _fsync_directory(self._transaction_root.parent)
        self._closed = True

    def rollback(self) -> None:
        if self._closed:
            return
        self._journal["phase"] = "rolling_back"
        _write_journal(self._transaction_root, self._journal)
        _restore_from_journal(
            layout=self._layout,
            transaction_root=self._transaction_root,
            journal=self._journal,
            transaction_id=self._plan_id,
            lock_nonce=self._lock_nonce,
        )
        shutil.rmtree(self._transaction_root)
        _fsync_directory(self._transaction_root.parent)
        self._closed = True


@contextmanager
def file_transaction(
    *,
    layout: RulersLayout,
    plan_id: str,
) -> Iterator[FileTransaction]:
    try:
        transaction_root = layout.transaction_root(plan_id)
    except UnsafeRulersPathError as exc:
        raise TransactionError(f"Unsafe transaction ID: {plan_id}") from exc
    with _acquire_maintenance_lock(layout=layout, plan_id=plan_id) as lease:
        transaction = FileTransaction(
            layout=layout,
            plan_id=plan_id,
            transaction_root=transaction_root,
            lock_nonce=lease.nonce,
        )
        initialized = False
        try:
            transaction._initialize()
            initialized = True
            yield transaction
        except BaseException:
            if not initialized:
                if transaction._owns_transaction_root:
                    lease.retain()
                raise
            try:
                transaction.rollback()
            except BaseException:
                lease.retain()
                raise
            raise
        else:
            try:
                transaction.commit()
            except BaseException:
                lease.retain()
                raise


def _is_valid_current_transaction(
    *,
    layout: RulersLayout,
    transaction_root: Path,
    transaction_id: str,
    lock_path: Path,
) -> bool:
    journal_path = transaction_root / _JOURNAL_NAME
    if (
        transaction_root.is_symlink()
        or not transaction_root.is_dir()
        or not _lexists(journal_path)
        or journal_path.is_symlink()
        or not journal_path.is_file()
        or not _lexists(lock_path)
        or lock_path.is_symlink()
        or not lock_path.is_file()
    ):
        return False
    try:
        lock_payload, _ = _read_lock(lock_path)
        if lock_payload["plan_id"] != transaction_id:
            return False
        journal = _load_journal(transaction_root)
        _validate_journal(
            layout=layout,
            transaction_root=transaction_root,
            journal=journal,
            transaction_id=transaction_id,
            lock_nonce=lock_payload["nonce"],
        )
    except Exception:
        return False
    return True


def find_incomplete_transaction(
    layout: RulersLayout,
    current_transaction_id: str | None = None,
) -> Path | None:
    cold_root, lock_path, recovery_path = _transaction_paths(layout)
    if not _lexists(cold_root):
        return None
    if cold_root.is_symlink() or not cold_root.is_dir():
        return cold_root
    if _lexists(recovery_path):
        return recovery_path

    transaction_roots = _cold_transaction_entries(
        cold_root,
        lock_path,
        recovery_path,
    )
    current_root: Path | None = None
    if current_transaction_id is not None:
        try:
            current_root = layout.transaction_root(current_transaction_id)
        except UnsafeRulersPathError:
            current_root = None
    ignored_current = False
    for transaction_root in transaction_roots:
        valid_current = (
            current_root is not None
            and transaction_root == current_root
            and _is_valid_current_transaction(
                layout=layout,
                transaction_root=transaction_root,
                transaction_id=current_transaction_id,
                lock_path=lock_path,
            )
        )
        if valid_current:
            ignored_current = True
            continue
        return transaction_root

    if ignored_current:
        return None
    return lock_path if _lexists(lock_path) else None


def _blocked_transaction_snapshot(
    *,
    artifacts: Sequence[TransactionArtifactFact],
    transaction_id: str | None = None,
    lock_nonce: str | None = None,
    error: BaseException | str,
) -> TransactionSnapshot:
    error_text = error if isinstance(error, str) else str(error)
    if not error_text:
        error_text = type(error).__name__
    return TransactionSnapshot(
        incomplete_present=True,
        artifacts=tuple(artifacts),
        transaction_id=transaction_id,
        lock_nonce=lock_nonce,
        actions=(),
        requires_replan=True,
        semantic_error=error_text,
    )


def _scan_incomplete_transaction(layout: RulersLayout) -> TransactionSnapshot:
    """Capture one immutable, role-bound snapshot of incomplete transaction facts."""
    artifacts: list[TransactionArtifactFact] = []
    contents: dict[str, tuple[Path, bytes]] = {}
    unsafe_errors: list[BaseException] = []
    try:
        cold_root, lock_path, recovery_path = _transaction_paths(layout)
    except (OSError, TransactionError, UnsafeRulersPathError) as exc:
        return _blocked_transaction_snapshot(artifacts=(), error=exc)
    if not _lexists(cold_root):
        return TransactionSnapshot(False, (), None, None, (), False, None)
    if cold_root.is_symlink() or not cold_root.is_dir():
        return _blocked_transaction_snapshot(
            artifacts=(), error="Transactions root is not a regular directory"
        )
    try:
        entries = sorted(cold_root.iterdir())
    except OSError as exc:
        return _blocked_transaction_snapshot(artifacts=(), error=exc)

    marker_present = _lexists(recovery_path)
    lock_present = _lexists(lock_path)
    def capture(role: str, path: Path) -> None:
        if not _lexists(path):
            return
        if path.is_symlink() or not path.is_file():
            unsafe_errors.append(TransactionError(f"{role} artifact is not a regular file"))
            return
        try:
            content = path.read_bytes()
        except OSError as exc:
            unsafe_errors.append(exc)
            return
        relative = path.relative_to(layout.project_root).as_posix()
        artifacts.append(TransactionArtifactFact(role, relative, _sha256(content)))
        contents[role] = (path, content)

    capture("recovery_lease" if marker_present else "maintenance_lock", lock_path)
    capture("recovery_marker", recovery_path)
    transaction_entries = [entry for entry in entries if entry not in {lock_path, recovery_path}]
    transaction_root: Path | None = None
    if len(transaction_entries) == 1:
        candidate_root = transaction_entries[0]
        unsafe_root = candidate_root.is_symlink() or not candidate_root.is_dir()
        unsafe_root = unsafe_root or candidate_root.resolve(strict=False) != candidate_root
        if unsafe_root:
            unsafe_errors.append(TransactionError("Transaction root is not a canonical directory"))
        else:
            transaction_root = candidate_root
            capture("journal", transaction_root / _JOURNAL_NAME)
    elif len(transaction_entries) > 1:
        unsafe_errors.append(TransactionError("Incomplete transaction root is missing or ambiguous"))

    incomplete_present = bool(marker_present or lock_present or transaction_entries or unsafe_errors)
    if not incomplete_present:
        return TransactionSnapshot(False, (), None, None, (), False, None)
    artifacts.sort(key=lambda value: (value.role, value.path))
    if unsafe_errors:
        return _blocked_transaction_snapshot(artifacts=artifacts, error=unsafe_errors[0])
    primary_role = "recovery_marker" if marker_present else "maintenance_lock"
    primary = contents.get(primary_role)
    if primary is None:
        return _blocked_transaction_snapshot(
            artifacts=artifacts, error="Incomplete transaction has no maintenance lock evidence"
        )
    transaction_id: str | None = None
    lock_nonce: str | None = None
    try:
        primary_path, primary_content = primary
        payload = _decode_lock(primary_content, primary_path)
        transaction_id = payload["plan_id"]
        lock_nonce = payload["nonce"]
        if not marker_present and _pid_is_active(payload["pid"]):
            raise TransactionError("Active maintenance writer cannot be inspected as a crash")
        lease = contents.get("recovery_lease")
        if lease is not None:
            lease_payload = _decode_lock(lease[1], lease[0])
            if lease_payload["plan_id"] != transaction_id:
                raise TransactionError("Recovery lease belongs to another transaction")
            if _pid_is_active(lease_payload["pid"]):
                raise TransactionError("Active transaction recovery cannot be inspected")
        if transaction_root is None:
            return TransactionSnapshot(True, tuple(artifacts), transaction_id, lock_nonce, (), True, None)
        expected_root = layout.transaction_root(transaction_id)
        if transaction_root != expected_root:
            raise TransactionError("Transaction root does not match maintenance lock evidence")
        journal_artifact = contents.get("journal")
        if journal_artifact is None:
            _validate_unjournaled_scaffold(transaction_root)
            return TransactionSnapshot(True, tuple(artifacts), transaction_id, lock_nonce, (), True, None)
        journal = _decode_journal(journal_artifact[1], journal_artifact[0])
        validated = _validate_journal(
            layout=layout,
            transaction_root=transaction_root,
            journal=journal,
            transaction_id=transaction_id,
            lock_nonce=lock_nonce,
        )
        if journal_artifact[0].read_bytes() != journal_artifact[1]:
            raise TransactionError("Transaction journal changed during inspection")
    except (OSError, TransactionError, UnsafeRulersPathError) as exc:
        return _blocked_transaction_snapshot(
            artifacts=artifacts,
            transaction_id=transaction_id,
            lock_nonce=lock_nonce,
            error=exc,
        )
    actions = tuple(
        InspectedTransactionAction(
            index=index,
            path=entry["path"],
            kind=entry["kind"],
            original_sha256=entry["original_sha256"],
            snapshot_ref=entry["snapshot_ref"],
            snapshot_sha256=entry["snapshot_sha256"],
            original_existed=entry["original_existed"],
            phase=entry["phase"],
        )
        for index, (entry, _snapshot_content) in enumerate(validated)
    )
    return TransactionSnapshot(
        True, tuple(artifacts), transaction_id, lock_nonce, actions, False, None
    )


def inspect_incomplete_transaction_evidence(layout: RulersLayout) -> TransactionSnapshot:
    """Return the scanner's tolerant snapshot of incomplete transaction facts."""
    return _scan_incomplete_transaction(layout)


def inspect_incomplete_transaction(layout: RulersLayout) -> InspectedTransaction | None:
    """Adapt one trusted scanner snapshot to the strict recovery contract."""
    snapshot = _scan_incomplete_transaction(layout)
    if not snapshot.incomplete_present:
        return None
    if snapshot.semantic_error is not None:
        raise TransactionError(snapshot.semantic_error)
    if snapshot.transaction_id is None or snapshot.lock_nonce is None:
        raise TransactionError("Incomplete transaction evidence is missing identity")

    artifacts = {artifact.role: artifact for artifact in snapshot.artifacts}
    lock = artifacts.get("recovery_marker") or artifacts.get("maintenance_lock")
    if lock is None:
        raise TransactionError("Incomplete transaction has no maintenance lock evidence")
    journal = artifacts.get("journal")
    return InspectedTransaction(
        transaction_id=snapshot.transaction_id,
        actions=snapshot.actions,
        lock_path=lock.path,
        lock_sha256=lock.sha256,
        lock_nonce=snapshot.lock_nonce,
        journal_path=None if journal is None else journal.path,
        journal_sha256=None if journal is None else journal.sha256,
        requires_replan=snapshot.requires_replan,
    )


def _validate_unjournaled_scaffold(transaction_root: Path) -> None:
    if not transaction_root.exists():
        return
    if transaction_root.is_symlink() or not transaction_root.is_dir():
        raise TransactionError("Unjournaled transaction root is unsafe")
    snapshots = transaction_root / _SNAPSHOTS_DIR
    if not set(transaction_root.iterdir()).issubset({snapshots}):
        raise TransactionError("Unjournaled transaction root contains unknown files")
    if snapshots.exists() and (
        snapshots.is_symlink()
        or not snapshots.is_dir()
        or any(snapshots.iterdir())
    ):
        raise TransactionError("Unjournaled transaction snapshots are not empty")


def _remove_unjournaled_scaffold(transaction_root: Path) -> None:
    _validate_unjournaled_scaffold(transaction_root)
    if transaction_root.exists():
        shutil.rmtree(transaction_root)
        _fsync_directory(transaction_root.parent)


def restore_transaction(
    *,
    layout: RulersLayout,
    transaction_id: str,
    expected_lock_sha256: str | None = None,
    expected_lock_nonce: str | None = None,
) -> tuple[str, ...]:
    try:
        transaction_root = layout.transaction_root(transaction_id)
    except UnsafeRulersPathError as exc:
        raise TransactionError(f"Unsafe transaction ID: {transaction_id}") from exc
    cold_root, lock, marker = _transaction_paths(layout)
    resuming = _lexists(marker)
    evidence_path = marker if resuming else lock
    if not _lexists(evidence_path):
        raise TransactionError("No maintenance lock evidence exists for recovery")
    payload, lock_content = _read_lock(evidence_path)
    if payload["plan_id"] != transaction_id:
        raise TransactionError("Maintenance lock belongs to another transaction")
    if not resuming and _pid_is_active(payload["pid"]):
        raise TransactionError("Active maintenance writer cannot be recovered")

    journal_path = transaction_root / _JOURNAL_NAME
    lock_only = not _lexists(journal_path)
    lock_hash = _sha256(lock_content)
    if resuming or lock_only:
        if expected_lock_sha256 is None or expected_lock_nonce is None:
            raise TransactionError("Recovery requires reviewed lock preconditions")
        if expected_lock_sha256 != lock_hash or expected_lock_nonce != payload["nonce"]:
            raise TransactionError("Recovery lock preconditions changed")
    else:
        if expected_lock_sha256 is not None and expected_lock_sha256 != lock_hash:
            raise TransactionError("Maintenance lock hash changed")
        if expected_lock_nonce is not None and expected_lock_nonce != payload["nonce"]:
            raise TransactionError("Maintenance lock nonce changed")

    if not resuming:
        try:
            os.replace(lock, marker)
        except OSError as exc:
            raise TransactionError("Could not claim maintenance lock evidence") from exc
        _fsync_directory(cold_root)
        claimed_payload, claimed_content = _read_lock(marker)
        if claimed_content != lock_content or claimed_payload != payload:
            raise TransactionError("Maintenance lock changed while recovery was claimed")

    lease = _acquire_recovery_lease(
        cold_root=cold_root,
        lock_path=lock,
        plan_id=transaction_id,
    )
    try:
        claimed_payload, claimed_content = _read_lock(marker)
        if claimed_content != lock_content or claimed_payload != payload:
            raise TransactionError("Recovery marker evidence changed")
        if lock_only:
            changed: tuple[str, ...] = ()
            _remove_unjournaled_scaffold(transaction_root)
        else:
            journal = _load_journal(transaction_root)
            _validate_journal(
                layout=layout,
                transaction_root=transaction_root,
                journal=journal,
                transaction_id=transaction_id,
                lock_nonce=payload["nonce"],
            )
            journal["phase"] = "rolling_back"
            _write_journal(transaction_root, journal)
            changed = _restore_from_journal(
                layout=layout,
                transaction_root=transaction_root,
                journal=journal,
                transaction_id=transaction_id,
                lock_nonce=payload["nonce"],
            )
            shutil.rmtree(transaction_root)
            _fsync_directory(cold_root)
        marker.unlink()
        _fsync_directory(cold_root)
    except BaseException:
        _remove_owned_lock(lease)
        raise
    _remove_owned_lock(lease)
    return changed
