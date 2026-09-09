from __future__ import annotations

import copy
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch as mock_patch


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skills" / "ai-rulers-init"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from tests.ai_rulers_test_support import (
    materialize_v2_fixture,
    snapshot_project,
    write_profile as support_write_profile,
)
from rulers_lib.domains import load_domain_registry
from rulers_lib.plans import (
    create_plan,
    finalize_plan,
    load_plan,
    plan_summary,
    validate_plan,
    write_plan_bundle,
)
from rulers_lib.paths import resolve_layout
from rulers_lib.reconcile import (
    EvidenceRecord,
    ProfileChange,
    affected_domains,
    diff_profiles,
    domain_actions,
    parse_profile,
)
from rulers_lib.state import state_json
from rulers_lib.transactions import file_transaction
import rulers_lib.plans as plans_module


RULERS_DIR = "documents/custom-rulers"


def write_profile(
    project: Path,
    rows: list[tuple[str, str, str, str, str]],
    *,
    rulers_dir: str,
) -> Path:
    return support_write_profile(
        project,
        rows,
        unresolved=[("owner approval", "activation", "core", "owner")],
        rulers_dir=rulers_dir,
    )


def _profile_text(rows: list[tuple[str, str, str, str, str]]) -> str:
    body = "\n".join(
        f"| {content} | {basis} | {evidence} | {scope} | {confidence} |"
        for content, basis, evidence, scope, confidence in rows
    )
    return f"""# 项目画像

## 1. 当前有效事实与约束

| 内容 | 依据类型 | 证据 | 作用域 | 置信度 |
| --- | --- | --- | --- | --- |
{body}

## 阻塞性未决问题

| 问题 | 重要原因 | 作用域 | 必需审阅人 |
| --- | --- | --- | --- |
| owner approval | activation | core | owner |
"""


def _record(
    content: str,
    basis: str,
    evidence: tuple[str, ...],
    scopes: tuple[str, ...],
) -> EvidenceRecord:
    return EvidenceRecord(content, basis, evidence, scopes, "high")  # type: ignore[arg-type]


def _snapshot_without_rulers_cold(
    project: Path,
    rulers_dir: str = RULERS_DIR,
) -> dict[str, tuple[bytes, int]]:
    snapshot = snapshot_project(project, exclude_cold=False)
    cold_prefixes = (
        f"{rulers_dir}/.plans/",
        f"{rulers_dir}/.transactions/",
    )
    return {
        relative: content
        for relative, content in snapshot.items()
        if not relative.startswith(cold_prefixes)
    }


def _current_fingerprints() -> tuple[dict[str, str], dict[str, str]]:
    with tempfile.TemporaryDirectory() as temp_dir:
        plan = create_plan(
            skill_root=SKILL_ROOT,
            project_root=Path(temp_dir),
            rulers_dir=RULERS_DIR,
        )
    return plan["template"], plan["preconditions"]["policy"]


def _materialize_current_state(project: Path) -> Path:
    state_path, state = materialize_v2_fixture(
        project,
        "schema2_runtime_ready.json",
    )
    template, policy = _current_fingerprints()
    state["schema_version"] = 3
    state["template_version"] = template["version"]
    state["template_fingerprint"] = template["fingerprint"]
    state["policy"]["fingerprint"] = policy["fingerprint"]
    state["profile"]["reviewed_sha256"] = state["profile"]["content_sha256"]
    registry = load_domain_registry(SKILL_ROOT)
    for domain, domain_state in state["domains"].items():
        domain_state["requires_active"] = list(registry[domain]["requires_active"])
    state_path.write_text(state_json(state), encoding="utf-8")
    return state_path


class UnifiedProfileAndPlanTest(unittest.TestCase):
    def test_profile_parser_accepts_observed_approved_and_rejects_unknown_basis_or_scope(self) -> None:
        text = _profile_text(
            [
                ("Python runtime", "Observed", "pyproject.toml<br>README.md", "core, backend", "high"),
                ("Release approval", "approved", "owner review", "delivery", "high"),
            ]
        )
        snapshot = parse_profile(
            text,
            allowed_scopes={"core", "backend", "delivery"},
        )

        self.assertEqual(("owner approval",), snapshot.unresolved)
        self.assertEqual(("backend", "core"), snapshot.records[0].scopes)
        self.assertEqual("observed", snapshot.records[0].basis)
        self.assertEqual(("README.md", "pyproject.toml"), snapshot.records[0].evidence)

        for bad_row, fragment in (
            (("Unknown basis", "guessed", "README.md", "core", "low"), "basis"),
            (("Unknown scope", "observed", "README.md", "mobile", "low"), "scope"),
        ):
            with self.subTest(fragment=fragment):
                with self.assertRaisesRegex(ValueError, rf"line 7.*{fragment}"):
                    parse_profile(
                        _profile_text([bad_row]),
                        allowed_scopes={"core"},
                    )

        unresolved_row = "| owner approval | activation | core | owner |"
        for replacement, fragment in (
            ("| owner approval |  | core | owner |", "reason"),
            ("| owner approval | activation | mobile | owner |", "scope"),
            ("| owner approval | activation | core |  |", "reviewer"),
            (f"{unresolved_row}\n{unresolved_row}", "duplicate"),
        ):
            with self.subTest(unresolved=fragment):
                invalid = _profile_text(
                    [("Python runtime", "observed", "pyproject.toml", "core", "high")]
                ).replace(unresolved_row, replacement)
                with self.assertRaisesRegex(ValueError, fragment):
                    parse_profile(invalid, allowed_scopes={"core"})

    def test_approved_to_observed_same_content_and_scope_is_evidence_only(self) -> None:
        reviewed = parse_profile(
            _profile_text([("Python runtime", "approved", "owner", "core", "high")]),
            allowed_scopes={"core"},
        )
        candidate = parse_profile(
            _profile_text([("Python runtime", "observed", "pyproject.toml", "core", "high")]),
            allowed_scopes={"core"},
        )

        changes = diff_profiles(reviewed, candidate)

        self.assertEqual(("evidence_only",), tuple(change.kind for change in changes))
        self.assertEqual(
            frozenset(),
            affected_domains(
                changes=changes,
                changed_paths=(),
                registry={"core": {"target_dir": "core", "detection_hints": [], "requires_active": []}},
                index_hints={},
            ),
        )

        confidence_changed = diff_profiles(
            parse_profile(
                _profile_text([("Python runtime", "observed", "pyproject.toml", "core", "high")]),
                allowed_scopes={"core"},
            ),
            parse_profile(
                _profile_text([("Python runtime", "observed", "pyproject.toml", "core", "low")]),
                allowed_scopes={"core"},
            ),
        )
        self.assertEqual(("changed",), tuple(change.kind for change in confidence_changed))

    def test_unique_approved_to_conflicting_observed_is_contradicted(self) -> None:
        reviewed = parse_profile(
            _profile_text([("Python 3.13", "approved", "owner", "backend", "high")]),
            allowed_scopes={"backend", "core"},
        )
        candidate = parse_profile(
            _profile_text([("Python 3.14", "observed", "pyproject.toml", "backend", "high")]),
            allowed_scopes={"backend", "core"},
        )

        changes = diff_profiles(reviewed, candidate)

        self.assertEqual(1, len(changes))
        self.assertEqual("contradicted", changes[0].kind)
        self.assertEqual("Python 3.13", changes[0].before.content)  # type: ignore[union-attr]
        self.assertEqual("Python 3.14", changes[0].after.content)  # type: ignore[union-attr]

    def test_ambiguous_text_change_is_removed_plus_added(self) -> None:
        reviewed = parse_profile(
            _profile_text(
                [
                    ("Python 3.12", "observed", "a", "backend", "high"),
                    ("Python 3.13", "observed", "b", "backend", "high"),
                ]
            ),
            allowed_scopes={"backend", "core"},
        )
        candidate = parse_profile(
            _profile_text(
                [
                    ("Python 3.14", "observed", "c", "backend", "high"),
                    ("Python 3.15", "observed", "d", "backend", "high"),
                ]
            ),
            allowed_scopes={"backend", "core"},
        )

        changes = diff_profiles(reviewed, candidate)

        self.assertEqual(2, sum(change.kind == "removed" for change in changes))
        self.assertEqual(2, sum(change.kind == "added" for change in changes))
        self.assertFalse(any(change.kind in {"changed", "contradicted"} for change in changes))

    def test_affected_domains_unions_profile_paths_index_hints_and_core_fallback(self) -> None:
        registry = {
            domain: {
                "target_dir": domain,
                "detection_hints": hints,
                "requires_active": [],
            }
            for domain, hints in {
                "core": [],
                "backend": ["server"],
                "database": ["migrations"],
                "frontend-web": ["web"],
            }.items()
        }
        change = ProfileChange(
            "changed",
            _record("old", "observed", ("a",), ("backend",)),
            _record("new", "observed", ("b",), ("backend",)),
        )

        affected = affected_domains(
            changes=[change],
            changed_paths=["migrations/001.sql", "ui/button.tsx", "unclassified/data.bin"],
            registry=registry,
            index_hints={"frontend-web": ["ui/**"]},
        )

        self.assertEqual(
            frozenset({"core", "backend", "database", "frontend-web"}),
            affected,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            _materialize_current_state(project)
            with self.assertRaisesRegex(ValueError, "changed path"):
                create_plan(
                    skill_root=SKILL_ROOT,
                    project_root=project,
                    rulers_dir=RULERS_DIR,
                    changed_paths=["missing.py"],
                )

            changed_path = project / "server/new.py"
            changed_path.parent.mkdir()
            changed_path.write_text("changed", encoding="utf-8")
            changed_only = create_plan(
                skill_root=SKILL_ROOT,
                project_root=project,
                rulers_dir=RULERS_DIR,
                changed_paths=["server/new.py"],
            )
            self.assertEqual("reconcile", changed_only["operation"])
            self.assertIsNone(changed_only["candidate_profile"])
            self.assertEqual(
                ["server/new.py"],
                [
                    fact["path"]
                    for fact in changed_only["preconditions"]["operation_inputs"][
                        "changed_paths"
                    ]
                ],
            )
            self.assertIn("backend", changed_only["affected_domains"])

            forged_retire = copy.deepcopy(changed_only)
            forged_retire["domain_actions"]["backend"] = "retire"
            forged_retire = finalize_plan(forged_retire)
            self.assertIn(
                "retired_domains",
                " ".join(
                    issue.message
                    for issue in validate_plan(forged_retire, skill_root=SKILL_ROOT)
                ),
            )

            forged_read = copy.deepcopy(changed_only)
            fake_fact = {"path": "server/missing.py", "sha256": "sha256:" + "4" * 64}
            forged_read["preconditions"]["operation_inputs"]["changed_paths"] = [
                fake_fact
            ]
            forged_read["preconditions"]["read_set"] = [
                fact
                for fact in forged_read["preconditions"]["read_set"]
                if fact["path"] != "server/new.py"
            ] + [fake_fact]
            forged_read["preconditions"]["read_set"].sort(key=lambda fact: fact["path"])
            forged_read["affected_domains"] = ["backend", "core"]
            forged_read["domain_actions"]["backend"] = "downgrade"
            forged_read = finalize_plan(forged_read)
            self.assertIn(
                "operation input",
                " ".join(
                    issue.message
                    for issue in validate_plan(forged_read, skill_root=SKILL_ROOT)
                ),
            )

    def test_security_change_expands_to_delivery(self) -> None:
        registry = load_domain_registry(SKILL_ROOT)
        change = ProfileChange(
            "changed",
            _record("old auth", "observed", ("a",), ("security",)),
            _record("new auth", "observed", ("b",), ("security",)),
        )

        affected = affected_domains(
            changes=[change],
            changed_paths=(),
            registry=registry,
            index_hints={},
        )

        self.assertTrue({"security", "delivery"}.issubset(affected))

    def test_retire_action_preserves_physical_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            rule = Path(temp_dir) / "documents/rulers/backend/INDEX.md"
            rule.parent.mkdir(parents=True)
            rule.write_text("human rule", encoding="utf-8")
            state = {
                "domains": {
                    "backend": {"review_status": "reviewed", "level": 2},
                    "core": {"review_status": "reviewed", "level": 1},
                }
            }

            actions = domain_actions(
                state=state,
                affected={"backend"},
                detected=set(),
                retired={"backend"},
            )

            self.assertEqual("retire", actions["backend"])
            self.assertEqual("human rule", rule.read_text(encoding="utf-8"))

    def test_same_payload_produces_same_plan_id_and_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            first = create_plan(
                skill_root=SKILL_ROOT,
                project_root=project,
                rulers_dir=RULERS_DIR,
            )
            plan_path = (
                project
                / RULERS_DIR
                / ".plans"
                / first["plan_id"]
                / "plan.json"
            )
            before = (plan_path.read_bytes(), plan_path.stat().st_mtime_ns)
            second = create_plan(
                skill_root=SKILL_ROOT,
                project_root=project,
                rulers_dir=RULERS_DIR,
            )
            with self.subTest(uid="PL-HASH-DETERMINISTIC"):
                self.assertEqual(first, second)
                self.assertEqual(before[0], plan_path.read_bytes())
                self.assertEqual(before[1], plan_path.stat().st_mtime_ns)
                self.assertRegex(
                    first["plan_sha256"],
                    r"^sha256:[0-9a-f]{64}$",
                )
                self.assertEqual(
                    first["plan_sha256"][7:23],
                    first["plan_id"],
                )

            with self.subTest(uid="PL-DECODE-PURE"), mock_patch(
                "pathlib.Path.read_bytes",
                side_effect=AssertionError("decoder touched filesystem"),
            ):
                decoded, issues = plans_module._decode_plan_document(first)
                self.assertIsNotNone(decoded)
                self.assertEqual([], issues)

            mutations = (
                (
                    "PL-TOP-EXTRA",
                    lambda plan: plan.__setitem__("extra", True),
                ),
                (
                    "PL-OPERATION-TYPE",
                    lambda plan: plan.__setitem__("operation", []),
                ),
                (
                    "PL-CHANGE-SHAPE",
                    lambda plan: plan.__setitem__(
                        "changes",
                        [{"kind": [], "count": 1, "scopes": ["core"]}],
                    ),
                ),
                (
                    "PL-DOMAIN-UNKNOWN",
                    lambda plan: (
                        plan.__setitem__("affected_domains", ["unknown"]),
                        plan.__setitem__(
                            "domain_actions",
                            {"unknown": "downgrade"},
                        ),
                    ),
                ),
                (
                    "PL-FILE-WRITESET-MISMATCH",
                    lambda plan: plan.__setitem__(
                        "file_actions",
                        [
                            {
                                "kind": "update",
                                "path": "other.txt",
                                "expected_sha256": None,
                            }
                        ],
                    ),
                ),
                (
                    "PL-DELETE-NO-HASH",
                    lambda plan: plan.__setitem__(
                        "file_actions",
                        [
                            {
                                "kind": "delete",
                                "path": "AGENTS.md",
                                "expected_sha256": None,
                            }
                        ],
                    ),
                ),
                (
                    "PL-DETAIL-UNKNOWN",
                    lambda plan: plan.__setitem__(
                        "detail_references",
                        ["note.txt"],
                    ),
                ),
                (
                    "PL-TEMPLATE-TAMPER",
                    lambda plan: plan["template"].__setitem__(
                        "version",
                        "forged",
                    ),
                ),
            )
            for uid, mutate in mutations:
                with self.subTest(uid=uid):
                    forged = copy.deepcopy(first)
                    mutate(forged)
                    forged = finalize_plan(forged)
                    self.assertTrue(
                        validate_plan(forged, skill_root=SKILL_ROOT),
                        uid,
                    )

        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            agents = project / "AGENTS.md"
            claude = project / "CLAUDE.md"
            agents.write_bytes(b"trusted-original")
            claude.write_bytes(b"trusted-claude")
            layout = resolve_layout(project, RULERS_DIR)
            with mock_patch(
                "rulers_lib.transactions.FileTransaction.rollback",
                side_effect=RuntimeError("simulated crash"),
            ):
                with self.assertRaisesRegex(RuntimeError, "simulated crash"):
                    with file_transaction(
                        layout=layout,
                        plan_id="trusted-repair",
                    ) as transaction:
                        transaction.replace_bytes(
                            Path("AGENTS.md"),
                            b"crash-write",
                        )
                        transaction.replace_bytes(
                            Path("CLAUDE.md"),
                            b"crash-claude",
                        )
                        raise ValueError("interrupt")
            lock = json.loads(
                layout.maintenance_lock_path.read_text(encoding="utf-8")
            )
            lock["pid"] = 999_999_999
            layout.maintenance_lock_path.write_text(
                json.dumps(lock),
                encoding="utf-8",
            )
            repair = create_plan(
                skill_root=SKILL_ROOT,
                project_root=project,
                rulers_dir=RULERS_DIR,
            )
            with self.subTest(uid="TX-PLAN-TRUSTED-CLOSURE"):
                self.assertEqual("repair", repair["operation"])
                self.assertEqual(
                    ["AGENTS.md", "CLAUDE.md"],
                    [action["path"] for action in repair["file_actions"]],
                )
                self.assertFalse(
                    validate_plan(repair, skill_root=SKILL_ROOT)
                )
                forged = copy.deepcopy(repair)
                forged["file_actions"].pop()
                forged["preconditions"]["write_set"].pop()
                forged = finalize_plan(forged)
                self.assertTrue(
                    validate_plan(forged, skill_root=SKILL_ROOT)
                )

            with self.subTest(uid="TX-PLAN-EVIDENCE-STALE"):
                journal_path = (
                    layout.transaction_root("trusted-repair")
                    / "journal.json"
                )
                journal_path.write_bytes(journal_path.read_bytes() + b" ")
                self.assertTrue(
                    validate_plan(repair, skill_root=SKILL_ROOT)
                )
    def test_create_plan_is_read_only_except_default_bundle(self) -> None:
        with self.subTest(uid="PR-CAPTURE-ONCE"), tempfile.TemporaryDirectory() as temp_dir:
            counters = {
                "template": 0,
                "policy": 0,
                "state": 0,
                "index": 0,
                "domains": 0,
            }

            def counted(name: str, function: object) -> object:
                def wrapper(*args: object, **kwargs: object) -> object:
                    counters[name] += 1
                    return function(*args, **kwargs)  # type: ignore[operator]

                return wrapper

            with (
                mock_patch(
                    "rulers_lib.plans._tree_fingerprint",
                    side_effect=counted(
                        "template",
                        plans_module._tree_fingerprint,
                    ),
                ),
                mock_patch(
                    "rulers_lib.plans._policy_fact",
                    side_effect=counted(
                        "policy",
                        plans_module._policy_fact,
                    ),
                ),
                mock_patch(
                    "rulers_lib.plans._read_state_fact",
                    side_effect=counted(
                        "state",
                        plans_module._read_state_fact,
                    ),
                ),
                mock_patch(
                    "rulers_lib.plans._index_hints",
                    side_effect=counted(
                        "index",
                        plans_module._index_hints,
                    ),
                ),
                mock_patch(
                    "rulers_lib.plans.detect_domains",
                    side_effect=counted(
                        "domains",
                        plans_module.detect_domains,
                    ),
                ),
            ):
                create_plan(
                    skill_root=SKILL_ROOT,
                    project_root=Path(temp_dir),
                    rulers_dir=RULERS_DIR,
                )
            self.assertEqual(
                {name: 1 for name in counters},
                counters,
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            materialize_v2_fixture(
                project,
                "schema2_runtime_ready.json",
            )
            nested = project / "src/.plans/keep.txt"
            nested.parent.mkdir(parents=True)
            nested.write_text("must remain visible", encoding="utf-8")
            before = _snapshot_without_rulers_cold(project)
            plan = create_plan(
                skill_root=SKILL_ROOT,
                project_root=project,
                rulers_dir=RULERS_DIR,
            )
            with self.subTest(uid="OP-SCHEMA2-UPGRADE"):
                self.assertEqual("upgrade", plan["operation"])
                self.assertEqual([], plan["changes"])
                self.assertIsNone(plan["candidate_profile"])
                self.assertEqual(before, _snapshot_without_rulers_cold(project))
                self.assertIn(
                    "src/.plans/keep.txt",
                    _snapshot_without_rulers_cold(project),
                )

        malformed_cases = (
            ("ST-PROFILE-SHAPE", lambda state: state.__setitem__("profile", "bad")),
            ("ST-POLICY-SHAPE", lambda state: state.__setitem__("policy", "bad")),
            ("ST-DOMAINS-SHAPE", lambda state: state.__setitem__("domains", "bad")),
            (
                "ST-MANAGED-SHAPE",
                lambda state: state.__setitem__("managed_files", "bad"),
            ),
            (
                "ST-LAST-OPERATION-SHAPE",
                lambda state: state.__setitem__("last_operation", "bad"),
            ),
            ("ST-TEMPLATE-SHAPE", lambda state: state.__setitem__("template", "bad")),
        )
        for uid, mutate in malformed_cases:
            with self.subTest(uid=uid), tempfile.TemporaryDirectory() as temp_dir:
                project = Path(temp_dir)
                state_path = _materialize_current_state(project)
                state = json.loads(state_path.read_text(encoding="utf-8"))
                mutate(state)
                state_path.write_text(state_json(state), encoding="utf-8")
                plan = create_plan(
                    skill_root=SKILL_ROOT,
                    project_root=project,
                    rulers_dir=RULERS_DIR,
                )
                self.assertEqual("repair", plan["operation"])
                self.assertTrue(plan["validation"])

        with self.subTest(uid="ST-UNSAFE-OWNERSHIP"), tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            state_path = _materialize_current_state(project)
            human = project / "human-owned.txt"
            human.write_text("human\n", encoding="utf-8")
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["managed_files"]["human-owned.txt"] = {
                "ownership": "managed",
                "rendered_sha256": plans_module.file_sha256(human),
            }
            state["domains"]["unknown"] = copy.deepcopy(
                state["domains"]["backend"]
            )
            state_path.write_text(state_json(state), encoding="utf-8")
            plan = create_plan(
                skill_root=SKILL_ROOT,
                project_root=project,
                rulers_dir=RULERS_DIR,
            )
            self.assertEqual("repair", plan["operation"])
            self.assertNotIn(
                "human-owned.txt",
                [action["path"] for action in plan["file_actions"]],
            )
            self.assertNotIn("unknown", plan["domain_actions"])

        operation_cases = (
            ("OP-READY-NOOP", "runtime_ready", (), "noop"),
            ("OP-UNFINISHED-RESUME", "profile_reviewed", (), "resume"),
            (
                "OP-CHANGED-RECONCILE",
                "runtime_ready",
                ("server/new.py",),
                "reconcile",
            ),
        )
        for uid, phase, changed, expected in operation_cases:
            with self.subTest(uid=uid), tempfile.TemporaryDirectory() as temp_dir:
                project = Path(temp_dir)
                state_path = _materialize_current_state(project)
                state = json.loads(state_path.read_text(encoding="utf-8"))
                state["phase"] = phase
                state_path.write_text(state_json(state), encoding="utf-8")
                if changed:
                    target = project / changed[0]
                    target.parent.mkdir()
                    target.write_text("changed\n", encoding="utf-8")
                plan = create_plan(
                    skill_root=SKILL_ROOT,
                    project_root=project,
                    rulers_dir=RULERS_DIR,
                    changed_paths=changed,
                )
                self.assertEqual(expected, plan["operation"])
    def test_noop_creates_no_bundle_and_changes_no_mtime(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            _materialize_current_state(project)
            before = snapshot_project(project, exclude_cold=False)

            plan = create_plan(
                skill_root=SKILL_ROOT,
                project_root=project,
                rulers_dir=RULERS_DIR,
            )

            self.assertEqual("noop", plan["operation"])
            self.assertEqual(before, snapshot_project(project, exclude_cold=False))
            self.assertFalse((project / RULERS_DIR / ".plans").exists())

            forged = copy.deepcopy(plan)
            forged["preconditions"]["write_set"] = [
                {"path": "unexpected.txt", "sha256": None}
            ]
            forged["file_actions"] = [
                {"kind": "update", "path": "unexpected.txt", "expected_sha256": None}
            ]
            forged = finalize_plan(forged)
            self.assertIn(
                "Noop",
                " ".join(
                    issue.message
                    for issue in validate_plan(forged, skill_root=SKILL_ROOT)
                ),
            )

        for uid, operation in (
            ("OP-EXISTING-STATE-FRESH", "fresh"),
            ("OP-READY-RECONCILE", "reconcile"),
            ("OP-READY-UPGRADE", "upgrade"),
            ("OP-READY-REPAIR", "repair"),
        ):
            with self.subTest(uid=uid), tempfile.TemporaryDirectory() as temp_dir:
                project = Path(temp_dir)
                _materialize_current_state(project)
                baseline = create_plan(
                    skill_root=SKILL_ROOT,
                    project_root=project,
                    rulers_dir=RULERS_DIR,
                )
                forged = copy.deepcopy(baseline)
                forged["operation"] = operation
                forged = finalize_plan(forged)
                self.assertTrue(
                    validate_plan(forged, skill_root=SKILL_ROOT),
                    uid,
                )

    def test_output_parent_absolute_and_symlink_escape_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, tempfile.TemporaryDirectory() as outside_dir:
            project = Path(temp_dir)
            outside = Path(outside_dir)
            for output in (
                outside / "plan.json",
                project / "inside-absolute" / "plan.json",
                project / "redirect" / "plan.json",
            ):
                if output.parent.name == "redirect":
                    output.parent.symlink_to(outside, target_is_directory=True)
                with self.subTest(output=output):
                    with self.assertRaises(ValueError):
                        create_plan(
                            skill_root=SKILL_ROOT,
                            project_root=project,
                            rulers_dir=RULERS_DIR,
                            output=output,
                        )

            relative_plan = create_plan(
                skill_root=SKILL_ROOT,
                project_root=project,
                rulers_dir=RULERS_DIR,
                output=Path("inside-relative/plan.json"),
            )
            self.assertTrue((project / "inside-relative/plan.json").is_file())
            self.assertEqual("profile_draft", relative_plan["expected_phase"])

        for forbidden_output in (
            Path(RULERS_DIR) / ".transactions" / "plan.json",
            Path(RULERS_DIR) / "RULERS_STATE.json",
            Path(RULERS_DIR) / "core" / "plan.json",
        ):
            with self.subTest(forbidden_output=forbidden_output), tempfile.TemporaryDirectory() as temp_dir:
                project = Path(temp_dir)
                with self.assertRaisesRegex(ValueError, r"rulers.*\.plans"):
                    create_plan(
                        skill_root=SKILL_ROOT,
                        project_root=project,
                        rulers_dir=RULERS_DIR,
                        output=forbidden_output,
                    )
                self.assertFalse((project / forbidden_output).exists())
                self.assertFalse((project / RULERS_DIR).exists())

        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            explicit_output = (
                Path(RULERS_DIR) / ".plans" / "explicit" / "plan.json"
            )
            explicit_plan = create_plan(
                skill_root=SKILL_ROOT,
                project_root=project,
                rulers_dir=RULERS_DIR,
                output=explicit_output,
            )
            self.assertTrue((project / explicit_output).is_file())
            self.assertFalse(validate_plan(explicit_plan, skill_root=SKILL_ROOT))

            with tempfile.TemporaryDirectory() as other_dir:
                other = Path(other_dir)
                with self.subTest(uid="BD-LAYOUT-BINDING"):
                    with self.assertRaisesRegex(ValueError, "layout"):
                        write_plan_bundle(
                            explicit_plan,
                            layout=resolve_layout(other, RULERS_DIR),
                            output=Path("other/plan.json"),
                        )
                    self.assertFalse((other / "other").exists())

    def test_plan_summary_excludes_profile_state_hashes_and_full_diff(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            _materialize_current_state(project)
            candidate = write_profile(
                project,
                [
                    (
                        "Python 3.14",
                        "observed",
                        "pyproject.toml",
                        "core",
                        "high",
                    )
                ],
                rulers_dir="candidate",
            )
            plan = create_plan(
                skill_root=SKILL_ROOT,
                project_root=project,
                rulers_dir=RULERS_DIR,
                candidate_profile=candidate,
            )
            plan_path = (
                project
                / RULERS_DIR
                / ".plans"
                / plan["plan_id"]
                / "plan.json"
            )

            with self.subTest(uid="SM-NO-SENSITIVE-DETAIL"):
                summary = plan_summary(plan, plan_path)
                rendered = json.dumps(
                    summary,
                    ensure_ascii=False,
                    sort_keys=True,
                )
                self.assertEqual("reconcile", summary["operation"])
                self.assertEqual("runtime_ready", summary["expected_phase"])
                self.assertNotIn("preconditions", summary)
                self.assertNotIn("file_actions", summary)
                self.assertNotIn("sha256", rendered)
                self.assertNotIn("Python 3.14", rendered)

            with self.subTest(uid="LD-COMPLETE-BUNDLE"):
                self.assertEqual(plan, load_plan(plan_path))
                patch_path = plan_path.parent / "profile.patch"
                patch_bytes = patch_path.read_bytes()
                self.assertTrue(patch_bytes)
                patch_path.unlink()
                with self.assertRaisesRegex(ValueError, "profile.patch"):
                    load_plan(plan_path)
                patch_path.write_bytes(patch_bytes)
                self.assertEqual(plan, load_plan(plan_path))

            with self.subTest(uid="PL-ACTION-TAMPER"):
                forged = copy.deepcopy(plan)
                forged["domain_actions"]["core"] = "keep"
                forged = finalize_plan(forged)
                self.assertTrue(
                    validate_plan(forged, skill_root=SKILL_ROOT)
                )

            with self.subTest(uid="BD-UNKNOWN-DETAIL-PREFLIGHT"):
                forged = copy.deepcopy(plan)
                forged["detail_references"] = ["note.txt"]
                forged = finalize_plan(forged)
                output = Path("unknown-detail/plan.json")
                with self.assertRaisesRegex(ValueError, "detail_references"):
                    write_plan_bundle(
                        forged,
                        layout=resolve_layout(project, RULERS_DIR),
                        output=output,
                    )
                self.assertFalse((project / output).exists())
                self.assertFalse((project / output.parent).exists())

            with self.subTest(uid="BD-EXISTING-DIFFERENT-NO-CLOBBER"):
                conflict = project / "conflict/plan.json"
                conflict.parent.mkdir()
                conflict.write_text("{}\n", encoding="utf-8")
                with self.assertRaises(ValueError):
                    write_plan_bundle(
                        plan,
                        layout=resolve_layout(project, RULERS_DIR),
                        output=Path("conflict/plan.json"),
                )
                self.assertEqual("{}\n", conflict.read_text(encoding="utf-8"))

            with self.subTest(uid="BD-NORMAL-FAILURE-CLEANS-PATCH"):
                original_open = os.open

                def fail_plan_marker(
                    target: object,
                    flags: int,
                    mode: int = 0o777,
                    *args: object,
                    **kwargs: object,
                ) -> int:
                    if (
                        Path(target).name == "plan.json"
                        and flags & os.O_CREAT
                    ):
                        raise OSError("forced plan marker failure")
                    return original_open(
                        target,
                        flags,
                        mode,
                        *args,
                        **kwargs,
                    )

                failed_output = Path("failed-bundle/plan.json")
                with mock_patch(
                    "rulers_lib.plans.os.open",
                    side_effect=fail_plan_marker,
                ):
                    with self.assertRaisesRegex(
                        OSError,
                        "forced plan marker failure",
                    ):
                        write_plan_bundle(
                            plan,
                            layout=resolve_layout(project, RULERS_DIR),
                            output=failed_output,
                        )
                self.assertFalse((project / failed_output).exists())
                self.assertFalse(
                    (project / failed_output.parent / "profile.patch").exists()
                )

        for attack in ("candidate-stale", "candidate-symlink", "candidate-directory"):
            with self.subTest(uid=f"LD-{attack.upper()}"), tempfile.TemporaryDirectory() as temp_dir:
                project = Path(temp_dir)
                candidate = write_profile(
                    project,
                    [
                        (
                            "Python seed",
                            "approved",
                            "owner",
                            "core",
                            "high",
                        )
                    ],
                    rulers_dir="seed",
                )
                plan = create_plan(
                    skill_root=SKILL_ROOT,
                    project_root=project,
                    rulers_dir=RULERS_DIR,
                    candidate_profile=candidate,
                )
                plan_path = (
                    project
                    / RULERS_DIR
                    / ".plans"
                    / plan["plan_id"]
                    / "plan.json"
                )
                if attack == "candidate-stale":
                    candidate.write_text("stale\n", encoding="utf-8")
                else:
                    candidate.unlink()
                    if attack == "candidate-symlink":
                        outside = project / "outside-profile.md"
                        outside.write_text("outside\n", encoding="utf-8")
                        candidate.symlink_to(outside)
                    else:
                        candidate.mkdir()
                with self.assertRaisesRegex(
                    ValueError,
                    "candidate Profile operation input",
                ):
                    load_plan(plan_path)

        for profile_mode in ("draft", "wrong_hash"):
            with self.subTest(uid=f"PR-READ-{profile_mode.upper()}"), tempfile.TemporaryDirectory() as temp_dir:
                project = Path(temp_dir)
                state_path = _materialize_current_state(project)
                state = json.loads(state_path.read_text(encoding="utf-8"))
                if profile_mode == "draft":
                    state["profile"]["status"] = "draft"
                else:
                    state["profile"]["reviewed_sha256"] = (
                        "sha256:" + "0" * 64
                    )
                state_path.write_text(state_json(state), encoding="utf-8")
                plan = create_plan(
                    skill_root=SKILL_ROOT,
                    project_root=project,
                    rulers_dir=RULERS_DIR,
                )
                profile_relative = f"{RULERS_DIR}/PROJECT_PROFILE.md"
                self.assertIsNone(
                    plan["preconditions"]["reviewed_profile"]
                )
                self.assertIn(
                    profile_relative,
                    {
                        fact["path"]
                        for fact in plan["preconditions"]["read_set"]
                    },
                )

if __name__ == "__main__":
    unittest.main()
