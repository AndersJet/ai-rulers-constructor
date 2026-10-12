from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skills" / "ai-rulers-init"
SCRIPTS_ROOT = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_ROOT))

from tests.ai_rulers_test_support import read_state, snapshot_project
from rulers_lib.paths import RulersLayout, resolve_layout
from rulers_lib.state import state_json
from rulers_lib.transactions import (
    DeleteAction,
    ReplaceAction,
    file_transaction,
    find_incomplete_transaction,
    inspect_incomplete_transaction,
    inspect_incomplete_transaction_evidence,
    maintenance_lock,
    restore_transaction,
    write_state_atomic,
)
from rulers_lib import transactions as transactions_module


def _layout(project: Path) -> RulersLayout:
    layout = resolve_layout(project, "documents/rulers")
    layout.rulers_root.mkdir(parents=True, exist_ok=True)
    return layout


def _run_crashing_transaction(
    project: Path,
    *,
    plan_id: str,
    target: str = "documents/rulers/target.bin",
    second_target: str | None = None,
) -> None:
    script = """
import os
import sys
from pathlib import Path
from rulers_lib.paths import resolve_layout
from rulers_lib.transactions import file_transaction

project = Path(sys.argv[1])
layout = resolve_layout(project, "documents/rulers")
with file_transaction(layout=layout, plan_id=sys.argv[2]) as transaction:
    transaction.replace_bytes(Path(sys.argv[3]), b"changed-after-crash")
    if sys.argv[4] != "-":
        transaction.replace_bytes(Path(sys.argv[4]), b"changed-after-crash")
    os._exit(17)
"""
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(SCRIPTS_ROOT)
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(project),
            plan_id,
            target,
            second_target or "-",
        ],
        cwd=project,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 17:
        raise AssertionError(result.stderr or result.stdout)


def _run_crashing_lock(
    project: Path,
    *,
    create_transaction_root: bool = False,
) -> None:
    script = """
import os
import json
import sys
from pathlib import Path
from rulers_lib.paths import resolve_layout
from rulers_lib.transactions import maintenance_lock

layout = resolve_layout(Path(sys.argv[1]), "documents/rulers")
with maintenance_lock(layout=layout):
    if sys.argv[2] == "create-root":
        lock = json.loads(layout.maintenance_lock_path.read_text(encoding="utf-8"))
        transaction_root = layout.transaction_root(lock["plan_id"])
        transaction_root.mkdir()
        (transaction_root / "snapshots").mkdir()
    os._exit(17)
"""
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(SCRIPTS_ROOT)
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(project),
            "create-root" if create_transaction_root else "lock-only",
        ],
        cwd=project,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 17:
        raise AssertionError(result.stderr or result.stdout)


def _lock_precondition(lock_path: Path) -> tuple[dict[str, object], str]:
    content = lock_path.read_bytes()
    payload = json.loads(content.decode("utf-8"))
    return payload, "sha256:" + hashlib.sha256(content).hexdigest()


def _business_snapshot(project: Path) -> dict[str, tuple[bytes, int]]:
    return {
        path: value
        for path, value in snapshot_project(project).items()
        if ".transactions" not in Path(path).parts
    }


class UnifiedTransactionsTest(unittest.TestCase):
    def test_lock_rejects_second_writer(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            layout = _layout(Path(temp_dir))

            with maintenance_lock(layout=layout):
                with self.assertRaises(RuntimeError):
                    with maintenance_lock(layout=layout):
                        self.fail("a second writer acquired the maintenance lock")

    def test_single_state_writer_uses_same_lock_and_cannot_race_apply(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            layout = _layout(project)
            state_path = layout.rulers_root / "RULERS_STATE.json"
            state_path.write_text(state_json({"schema_version": 3}), encoding="utf-8")

            with maintenance_lock(layout=layout):
                precondition = read_state(project)
                self.assertEqual(3, precondition["schema_version"])
                with self.assertRaises(RuntimeError):
                    with file_transaction(layout=layout, plan_id="racing-plan"):
                        self.fail("apply raced a single-State writer")
                self.assertTrue(
                    write_state_atomic(
                        state_path,
                        {"schema_version": 3, "phase": "reviewed"},
                    )
                )

    def test_only_touched_files_are_snapshotted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            layout = _layout(project)
            touched = layout.rulers_root / "touched.bin"
            untouched = layout.rulers_root / "untouched.bin"
            touched.write_bytes(b"old-touched-bytes")
            untouched.write_bytes(b"same-untouched-bytes")

            with file_transaction(layout=layout, plan_id="write-set") as transaction:
                changed = transaction.apply(
                    [
                        ReplaceAction(
                            "documents/rulers/touched.bin",
                            b"new-touched-bytes",
                        ),
                        ReplaceAction(
                            "documents/rulers/untouched.bin",
                            b"same-untouched-bytes",
                        ),
                    ]
                )
                self.assertEqual(("documents/rulers/touched.bin",), changed)
                transaction_root = layout.transactions_root / "write-set"
                snapshots = list((transaction_root / "snapshots").glob("*"))
                self.assertEqual(1, len(snapshots))
                journal = (transaction_root / "journal.json").read_bytes()
                self.assertNotIn(b"old-touched-bytes", journal)
                self.assertNotIn(b"new-touched-bytes", journal)

        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            layout = _layout(project)
            target = layout.rulers_root / "duplicate.bin"
            target.write_bytes(b"before-duplicate")

            with self.assertRaisesRegex(RuntimeError, "Duplicate transaction target"):
                with file_transaction(
                    layout=layout,
                    plan_id="duplicate-across-apply",
                ) as transaction:
                    transaction.replace_bytes(
                        Path("documents/rulers/duplicate.bin"),
                        b"first-write",
                    )
                    transaction.replace_bytes(
                        Path("documents/rulers/duplicate.bin"),
                        b"second-write",
                    )

            self.assertEqual(b"before-duplicate", target.read_bytes())
            self.assertFalse((layout.transactions_root / "duplicate-across-apply").exists())

    def test_exception_restores_bytes_and_removes_successful_rollback_journal(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            layout = _layout(project)
            target = layout.rulers_root / "target.bin"
            removed = layout.rulers_root / "removed.bin"
            claude = project / "CLAUDE.md"
            target.write_bytes(b"original-bytes\x00\xff")
            removed.write_bytes(b"private-original")
            removed.chmod(0o600)
            claude.write_bytes(b"private-claude-bytes\x00")
            claude.chmod(0o600)

            with self.assertRaisesRegex(ValueError, "stop apply"):
                with file_transaction(layout=layout, plan_id="rollback") as transaction:
                    self.assertTrue(
                        transaction.replace_bytes(
                            Path("documents/rulers/target.bin"),
                            b"replacement-bytes",
                        )
                    )
                    self.assertTrue(
                        transaction.remove(Path("documents/rulers/removed.bin"))
                    )
                    self.assertTrue(transaction.remove(Path("CLAUDE.md")))
                    raise ValueError("stop apply")

            self.assertEqual(b"original-bytes\x00\xff", target.read_bytes())
            self.assertEqual(b"private-original", removed.read_bytes())
            self.assertEqual(0o600, removed.stat().st_mode & 0o777)
            self.assertEqual(b"private-claude-bytes\x00", claude.read_bytes())
            self.assertEqual(0o600, claude.stat().st_mode & 0o777)
            self.assertFalse((layout.transactions_root / "rollback").exists())
            self.assertFalse(layout.maintenance_lock_path.exists())

            claude.unlink()
            with self.assertRaises(RuntimeError):
                with file_transaction(
                    layout=layout,
                    plan_id="do-not-create-root-special",
                ) as transaction:
                    transaction.replace_bytes(Path("CLAUDE.md"), b"not-allowed")
            self.assertFalse(claude.exists())

    def test_incomplete_transaction_is_discoverable_but_current_id_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            layout = _layout(project)
            target = layout.rulers_root / "target.bin"
            target.write_bytes(b"before-crash")
            _run_crashing_transaction(project, plan_id="crashed-plan")

            transaction_root = layout.transactions_root / "crashed-plan"
            payload, lock_hash = _lock_precondition(layout.maintenance_lock_path)
            self.assertEqual(transaction_root, find_incomplete_transaction(layout))
            self.assertIsNone(
                find_incomplete_transaction(
                    layout,
                    current_transaction_id="crashed-plan",
                )
            )
            journal_path = transaction_root / "journal.json"
            original_journal = journal_path.read_bytes()
            journal_path.write_bytes(b"{not-valid-json")
            self.assertEqual(
                transaction_root,
                find_incomplete_transaction(
                    layout,
                    current_transaction_id="crashed-plan",
                ),
            )
            journal_path.write_bytes(original_journal)
            mismatched = json.loads(original_journal.decode("utf-8"))
            mismatched["lock_nonce"] = "mismatched-lock-nonce"
            journal_path.write_text(json.dumps(mismatched), encoding="utf-8")
            self.assertEqual(
                transaction_root,
                find_incomplete_transaction(
                    layout,
                    current_transaction_id="crashed-plan",
                ),
            )
            journal_path.write_bytes(original_journal)
            os.replace(
                layout.maintenance_lock_path,
                layout.maintenance_recovery_path,
            )
            self.assertEqual(
                layout.maintenance_recovery_path,
                find_incomplete_transaction(layout),
            )
            self.assertEqual(
                ("documents/rulers/target.bin",),
                restore_transaction(
                    layout=layout,
                    transaction_id="crashed-plan",
                    expected_lock_sha256=lock_hash,
                    expected_lock_nonce=str(payload["nonce"]),
                ),
            )
            self.assertEqual(b"before-crash", target.read_bytes())
            self.assertFalse(layout.maintenance_recovery_path.exists())
            self.assertFalse(layout.maintenance_lock_path.exists())
            self.assertFalse(transaction_root.exists())

    def test_orphan_lock_before_journal_is_discoverable_and_requires_repair(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            layout = _layout(project)
            _run_crashing_lock(project, create_transaction_root=True)

            evidence = find_incomplete_transaction(layout)
            transaction_root = layout.transactions_root / "single-state-writer"
            self.assertEqual(transaction_root, evidence)
            payload, lock_hash = _lock_precondition(layout.maintenance_lock_path)
            with self.assertRaises(RuntimeError):
                restore_transaction(
                    layout=layout,
                    transaction_id=str(payload["plan_id"]),
                )
            self.assertTrue(layout.maintenance_lock_path.exists())
            self.assertEqual(
                (),
                restore_transaction(
                    layout=layout,
                    transaction_id=str(payload["plan_id"]),
                    expected_lock_sha256=lock_hash,
                    expected_lock_nonce=str(payload["nonce"]),
                ),
            )
            self.assertFalse(
                transaction_root.exists()
            )
            self.assertIsNone(find_incomplete_transaction(layout))

            missing = layout.transactions_root / "missing-marker-target"
            layout.maintenance_recovery_path.symlink_to(missing)
            self.assertEqual(
                layout.maintenance_recovery_path,
                find_incomplete_transaction(layout),
            )
            with self.assertRaises(RuntimeError):
                with maintenance_lock(layout=layout):
                    self.fail("writer ignored a dangling recovery marker")
            layout.maintenance_recovery_path.unlink()

            damaged = layout.transactions_root / "damaged-transaction"
            damaged.write_bytes(b"not-a-directory")
            self.assertEqual(damaged, find_incomplete_transaction(layout))
            self.assertEqual(
                damaged,
                find_incomplete_transaction(
                    layout,
                    current_transaction_id="damaged-transaction",
                ),
            )
            with self.assertRaises(RuntimeError):
                with maintenance_lock(layout=layout):
                    self.fail("writer ignored a damaged transaction artifact")
            damaged.unlink()

            layout.transactions_root.rmdir()
            layout.transactions_root.write_bytes(b"not-a-directory")
            self.assertEqual(
                layout.transactions_root,
                find_incomplete_transaction(layout),
            )
            with self.assertRaises(RuntimeError):
                with maintenance_lock(layout=layout):
                    self.fail("writer treated a cold-root file as no transaction")

    def test_active_lock_cannot_be_recovered(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            layout = _layout(Path(temp_dir))

            with maintenance_lock(layout=layout):
                payload, lock_hash = _lock_precondition(layout.maintenance_lock_path)
                with self.assertRaises(RuntimeError):
                    restore_transaction(
                        layout=layout,
                        transaction_id=str(payload["plan_id"]),
                        expected_lock_sha256=lock_hash,
                        expected_lock_nonce=str(payload["nonce"]),
                    )
                self.assertTrue(layout.maintenance_lock_path.exists())

        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            layout = _layout(project)
            target = layout.rulers_root / "target.bin"
            target.write_bytes(b"before-recovery-lease")
            _run_crashing_transaction(project, plan_id="recovery-lease")
            original_payload, original_hash = _lock_precondition(
                layout.maintenance_lock_path
            )
            os.replace(
                layout.maintenance_lock_path,
                layout.maintenance_recovery_path,
            )
            recovery_lease = {
                "plan_id": "recovery-lease",
                "pid": os.getpid(),
                "nonce": "active-recovery-lease",
            }
            layout.maintenance_lock_path.write_text(
                json.dumps(recovery_lease),
                encoding="utf-8",
            )

            with self.assertRaises(RuntimeError):
                restore_transaction(
                    layout=layout,
                    transaction_id="recovery-lease",
                    expected_lock_sha256=original_hash,
                    expected_lock_nonce=str(original_payload["nonce"]),
                )

            self.assertTrue(layout.maintenance_lock_path.exists())
            self.assertTrue(layout.maintenance_recovery_path.exists())
            recovery_lease["pid"] = original_payload["pid"]
            layout.maintenance_lock_path.write_text(
                json.dumps(recovery_lease),
                encoding="utf-8",
            )
            self.assertEqual(
                ("documents/rulers/target.bin",),
                restore_transaction(
                    layout=layout,
                    transaction_id="recovery-lease",
                    expected_lock_sha256=original_hash,
                    expected_lock_nonce=str(original_payload["nonce"]),
                ),
            )
            self.assertEqual(b"before-recovery-lease", target.read_bytes())
            self.assertFalse(layout.maintenance_lock_path.exists())
            self.assertFalse(layout.maintenance_recovery_path.exists())

    def test_reviewed_orphan_lock_recovery_clears_only_lock_and_requires_replan(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            layout = _layout(project)
            state_path = layout.rulers_root / "RULERS_STATE.json"
            state_path.write_text(state_json({"schema_version": 3}), encoding="utf-8")
            before = _business_snapshot(project)
            _run_crashing_lock(project)
            payload, lock_hash = _lock_precondition(layout.maintenance_lock_path)

            changed = restore_transaction(
                layout=layout,
                transaction_id=str(payload["plan_id"]),
                expected_lock_sha256=lock_hash,
                expected_lock_nonce=str(payload["nonce"]),
            )

            self.assertEqual((), changed)
            # Task 7 must translate this lock-only recovery into requires_replan.
            self.assertEqual(before, _business_snapshot(project))
            self.assertFalse(layout.maintenance_lock_path.exists())
            self.assertFalse(layout.maintenance_recovery_path.exists())

    def test_journal_parent_and_symlink_escape_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            sandbox = Path(temp_dir)
            project = sandbox / "project"
            layout = _layout(project)
            target = layout.rulers_root / "target.bin"
            target.write_bytes(b"safe-original")
            _run_crashing_transaction(project, plan_id="unsafe-journal")
            lock_payload, lock_hash = _lock_precondition(
                layout.maintenance_lock_path
            )

            def restore_unsafe_journal() -> tuple[str, ...]:
                return restore_transaction(
                    layout=layout,
                    transaction_id="unsafe-journal",
                    expected_lock_sha256=lock_hash,
                    expected_lock_nonce=str(lock_payload["nonce"]),
                )

            transaction_root = layout.transactions_root / "unsafe-journal"
            journal_path = transaction_root / "journal.json"
            original_journal = json.loads(journal_path.read_text(encoding="utf-8"))
            snapshot_path = transaction_root / original_journal["actions"][0][
                "snapshot_ref"
            ]
            snapshot_content = snapshot_path.read_bytes()
            snapshot_mode = snapshot_path.stat().st_mode & 0o777
            alternate_snapshot = transaction_root / "same-bytes-different-mode.bin"
            alternate_snapshot.write_bytes(snapshot_content)
            alternate_snapshot.chmod(0o777)
            snapshot_path.unlink()
            snapshot_path.symlink_to(alternate_snapshot)
            changed_bytes = target.read_bytes()
            changed_mode = target.stat().st_mode & 0o777

            with self.assertRaises(RuntimeError):
                restore_unsafe_journal()

            self.assertEqual(changed_bytes, target.read_bytes())
            self.assertEqual(changed_mode, target.stat().st_mode & 0o777)
            self.assertFalse(layout.maintenance_lock_path.exists())
            self.assertTrue(layout.maintenance_recovery_path.exists())
            self.assertTrue(journal_path.exists())
            snapshot_path.unlink()
            snapshot_path.write_bytes(snapshot_content)
            snapshot_path.chmod(snapshot_mode)

            parent_escape = json.loads(json.dumps(original_journal))
            parent_escape["actions"][0]["path"] = "../outside.bin"
            journal_path.write_text(json.dumps(parent_escape), encoding="utf-8")
            with self.assertRaises(RuntimeError):
                restore_unsafe_journal()
            self.assertFalse((sandbox / "outside.bin").exists())

            outside = sandbox / "outside"
            outside.mkdir()
            (layout.rulers_root / "escape-link").symlink_to(outside, target_is_directory=True)
            symlink_escape = json.loads(json.dumps(original_journal))
            symlink_escape["actions"][0]["path"] = (
                "documents/rulers/escape-link/victim.bin"
            )
            journal_path.write_text(json.dumps(symlink_escape), encoding="utf-8")
            with self.assertRaises(RuntimeError):
                restore_unsafe_journal()
            self.assertFalse((outside / "victim.bin").exists())

            journal_path.write_text(json.dumps(original_journal), encoding="utf-8")
            restore_unsafe_journal()
            self.assertEqual(b"safe-original", target.read_bytes())

            layout.transactions_root.rmdir()
            escaped_cold_root = sandbox / "escaped-cold-root"
            escaped_cold_root.mkdir()
            layout.transactions_root.symlink_to(
                escaped_cold_root,
                target_is_directory=True,
            )
            with self.assertRaises(RuntimeError):
                with maintenance_lock(layout=layout):
                    self.fail("maintenance lock escaped through the cold root")
            self.assertFalse((escaped_cold_root / "maintenance.lock").exists())

            ancestor_project = sandbox / "ancestor-project"
            redirected_layout = _layout(ancestor_project)
            original_documents = sandbox / "original-documents"
            (ancestor_project / "documents").rename(original_documents)
            escaped_documents = sandbox / "escaped-documents"
            (escaped_documents / "rulers").mkdir(parents=True)
            (ancestor_project / "documents").symlink_to(
                escaped_documents,
                target_is_directory=True,
            )
            with self.assertRaises(RuntimeError):
                with maintenance_lock(layout=redirected_layout):
                    self.fail("maintenance lock escaped through an ancestor symlink")
            self.assertFalse(
                (escaped_documents / "rulers" / ".transactions").exists()
            )

    def test_snapshot_hash_mismatch_stops_automatic_restore(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            layout = _layout(project)
            target = layout.rulers_root / "target.bin"
            target.write_bytes(b"trusted-original")
            _run_crashing_transaction(project, plan_id="tampered-snapshot")
            transaction_root = layout.transactions_root / "tampered-snapshot"
            journal_path = transaction_root / "journal.json"
            journal_content = journal_path.read_bytes()
            journal = json.loads(journal_content.decode("utf-8"))
            snapshot_path = transaction_root / journal["actions"][0]["snapshot_ref"]
            snapshot_content = snapshot_path.read_bytes()
            lock_content = layout.maintenance_lock_path.read_bytes()

            with mock.patch.object(
                transactions_module,
                "_scan_incomplete_transaction",
                wraps=transactions_module._scan_incomplete_transaction,
            ) as scanner:
                inspection = inspect_incomplete_transaction(layout)
                evidence = inspect_incomplete_transaction_evidence(layout)
            self.assertEqual(2, scanner.call_count)
            self.assertIsNotNone(inspection)
            assert inspection is not None
            self.assertIsNone(evidence.semantic_error)
            self.assertEqual(inspection.transaction_id, evidence.transaction_id)
            self.assertEqual(inspection.lock_nonce, evidence.lock_nonce)
            self.assertEqual(inspection.actions, evidence.actions)
            self.assertEqual(inspection.requires_replan, evidence.requires_replan)
            artifacts = {artifact.role: artifact for artifact in evidence.artifacts}
            self.assertEqual(inspection.lock_path, artifacts["maintenance_lock"].path)
            self.assertEqual(
                inspection.lock_sha256,
                artifacts["maintenance_lock"].sha256,
            )
            self.assertEqual(inspection.journal_path, artifacts["journal"].path)
            self.assertEqual(
                inspection.journal_sha256,
                artifacts["journal"].sha256,
            )
            self.assertEqual("tampered-snapshot", inspection.transaction_id)
            self.assertEqual(
                "documents/rulers/target.bin",
                inspection.actions[0].path,
            )
            self.assertEqual("snapshots/000000.bin", inspection.actions[0].snapshot_ref)

            lock_backup = project / "lock.backup"
            layout.maintenance_lock_path.rename(lock_backup)
            with self.assertRaises(RuntimeError):
                inspect_incomplete_transaction(layout)
            lock_backup.rename(layout.maintenance_lock_path)

            for attack in ("nonce", "id", "top", "kind", "phase"):
                with self.subTest(inspection_attack=attack):
                    if attack in {"nonce", "id"}:
                        lock = json.loads(lock_content.decode("utf-8"))
                        lock["nonce" if attack == "nonce" else "plan_id"] = "forged"
                        layout.maintenance_lock_path.write_text(
                            json.dumps(lock),
                            encoding="utf-8",
                        )
                    else:
                        attacked_journal = json.loads(journal_content.decode("utf-8"))
                        if attack == "top":
                            attacked_journal["extra"] = True
                        else:
                            attacked_journal["actions"][0].pop(attack)
                        journal_path.write_text(
                            json.dumps(attacked_journal),
                            encoding="utf-8",
                        )
                    blocked = inspect_incomplete_transaction_evidence(layout)
                    self.assertTrue(blocked.incomplete_present)
                    self.assertIsNotNone(blocked.semantic_error)
                    self.assertEqual((), blocked.actions)
                    self.assertTrue(blocked.requires_replan)
                    with self.assertRaises(RuntimeError):
                        inspect_incomplete_transaction(layout)
                    layout.maintenance_lock_path.write_bytes(lock_content)
                    journal_path.write_bytes(journal_content)

            alternate_snapshot = transaction_root / "alternate.bin"
            alternate_snapshot.write_bytes(snapshot_content)
            snapshot_path.unlink()
            snapshot_path.symlink_to(alternate_snapshot)
            blocked = inspect_incomplete_transaction_evidence(layout)
            self.assertIsNotNone(blocked.semantic_error)
            with self.assertRaises(RuntimeError):
                inspect_incomplete_transaction(layout)
            snapshot_path.unlink()
            snapshot_path.write_bytes(snapshot_content)

            ambiguous = layout.transactions_root / "second-transaction"
            ambiguous.mkdir()
            (ambiguous / "snapshots").mkdir()
            blocked = inspect_incomplete_transaction_evidence(layout)
            self.assertIsNotNone(blocked.semantic_error)
            with self.assertRaises(RuntimeError):
                inspect_incomplete_transaction(layout)
            (ambiguous / "snapshots").rmdir()
            ambiguous.rmdir()

            snapshot_path.write_bytes(b"tampered")

            with self.assertRaises(RuntimeError):
                restore_transaction(layout=layout, transaction_id="tampered-snapshot")

            self.assertEqual(b"changed-after-crash", target.read_bytes())
            self.assertTrue(transaction_root.exists())
            self.assertFalse(layout.maintenance_lock_path.exists())
            self.assertTrue(layout.maintenance_recovery_path.exists())

        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            layout = _layout(project)
            first = layout.rulers_root / "first.bin"
            second = layout.rulers_root / "second.bin"
            first.write_bytes(b"same-original")
            second.write_bytes(b"same-original")
            first.chmod(0o600)
            second.chmod(0o644)
            _run_crashing_transaction(
                project,
                plan_id="duplicate-snapshot-ref",
                target="documents/rulers/first.bin",
                second_target="documents/rulers/second.bin",
            )
            transaction_root = layout.transactions_root / "duplicate-snapshot-ref"
            journal_path = transaction_root / "journal.json"
            journal = json.loads(journal_path.read_text(encoding="utf-8"))
            journal["actions"][1]["snapshot_ref"] = journal["actions"][0][
                "snapshot_ref"
            ]
            journal_path.write_text(json.dumps(journal), encoding="utf-8")
            before = {
                path: (path.read_bytes(), path.stat().st_mode & 0o777)
                for path in (first, second)
            }

            with self.assertRaises(RuntimeError):
                restore_transaction(
                    layout=layout,
                    transaction_id="duplicate-snapshot-ref",
                )

            self.assertEqual(
                before,
                {
                    path: (path.read_bytes(), path.stat().st_mode & 0o777)
                    for path in (first, second)
                },
            )
            self.assertTrue(transaction_root.exists())
            self.assertTrue(
                layout.maintenance_lock_path.exists()
                or layout.maintenance_recovery_path.exists()
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            layout = _layout(project)
            first = layout.rulers_root / "first.bin"
            second = layout.rulers_root / "second.bin"
            first.write_bytes(b"same-original")
            second.write_bytes(b"same-original")
            _run_crashing_transaction(
                project,
                plan_id="duplicate-journal-target",
                target="documents/rulers/first.bin",
                second_target="documents/rulers/second.bin",
            )
            transaction_root = layout.transactions_root / "duplicate-journal-target"
            journal_path = transaction_root / "journal.json"
            journal = json.loads(journal_path.read_text(encoding="utf-8"))
            journal["actions"][1]["path"] = journal["actions"][0]["path"]
            journal_path.write_text(json.dumps(journal), encoding="utf-8")
            before = {path: path.read_bytes() for path in (first, second)}

            blocked = inspect_incomplete_transaction_evidence(layout)
            self.assertTrue(blocked.incomplete_present)
            self.assertIsNotNone(blocked.semantic_error)
            self.assertEqual((), blocked.actions)
            self.assertTrue(blocked.requires_replan)
            with self.assertRaisesRegex(RuntimeError, "Duplicate transaction target"):
                inspect_incomplete_transaction(layout)
            with self.assertRaisesRegex(RuntimeError, "Duplicate transaction target"):
                restore_transaction(
                    layout=layout,
                    transaction_id="duplicate-journal-target",
                )

            self.assertEqual(before, {path: path.read_bytes() for path in (first, second)})
            self.assertTrue(transaction_root.exists())

    def test_success_cleans_lock_and_transaction(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            layout = _layout(project)
            target = layout.rulers_root / "created.bin"

            for reserved in ("maintenance.lock", "maintenance.lock.recovery"):
                with self.subTest(reserved=reserved):
                    with self.assertRaises(ValueError):
                        layout.transaction_root(reserved)
                    with self.assertRaises(RuntimeError):
                        with file_transaction(layout=layout, plan_id=reserved):
                            self.fail("reserved cold-root name was accepted")

            for cold_target in (
                "documents/rulers/.plans/forged.json",
                "documents/rulers/.transactions/forged.json",
            ):
                with self.subTest(cold_target=cold_target):
                    with self.assertRaises(RuntimeError):
                        with file_transaction(
                            layout=layout,
                            plan_id="reject-cold-target",
                        ) as transaction:
                            transaction.replace_bytes(Path(cold_target), b"forged")

            with file_transaction(layout=layout, plan_id="success") as transaction:
                self.assertEqual(
                    ("documents/rulers/created.bin",),
                    transaction.apply(
                        [
                            ReplaceAction(
                                "documents/rulers/created.bin",
                                b"created",
                            ),
                            DeleteAction("documents/rulers/missing.bin"),
                        ]
                    ),
                )

            self.assertEqual(b"created", target.read_bytes())
            self.assertFalse((layout.transactions_root / "success").exists())
            self.assertFalse(layout.maintenance_lock_path.exists())
            self.assertFalse(layout.maintenance_recovery_path.exists())

    def test_atomic_state_write_preserves_mtime_on_zero_diff(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            layout = _layout(project)
            state = {"schema_version": 3, "phase": "runtime_ready"}
            state_path = layout.rulers_root / "RULERS_STATE.json"
            state_path.write_text(state_json(state), encoding="utf-8")
            timestamp = 1_700_000_000_123_456_789
            os.utime(state_path, ns=(timestamp, timestamp))
            before_mtime = state_path.stat().st_mtime_ns

            self.assertFalse(write_state_atomic(state_path, state))

            self.assertEqual(before_mtime, state_path.stat().st_mtime_ns)
            self.assertEqual(state, read_state(project))


if __name__ == "__main__":
    unittest.main()
