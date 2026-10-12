"""Raw evidence fixtures and public maintenance results, not semantic model scores."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.prepare_rule_quality_replay import METADATA, REVIEW, prepare
from scripts.runtime_fixture import SKILL_ROOT


class RuleQualityTest(unittest.TestCase):
    def call(self, target, *args, validator=False):
        script = "validate_rulers.py" if validator else "rulers_init.py"
        result = subprocess.run([sys.executable, str(SKILL_ROOT / "scripts" / script), *args],
                                cwd=target, capture_output=True, text=True,
                                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        self.assertEqual(0, result.returncode, result.stderr or result.stdout)
        return json.loads(result.stdout)

    def test_discovery_starts_from_raw_evidence_and_keeps_existing_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "raw"
            record = prepare(SKILL_ROOT, target, "conflict")
            self.assertFalse(record["synthetic_prestate_approval"])
            self.assertFalse((target / "documents/rulers").exists())
            self.assertFalse((target / ".rulers-work").exists())
            self.assertTrue((target / "workers/legacy_refund.py").is_file())
            before = (target / "notes.txt").read_bytes()
            with self.assertRaises(ValueError):
                prepare(SKILL_ROOT, target, "minimal")
            self.assertEqual(before, (target / "notes.txt").read_bytes())

    def test_greenfield_has_decisions_but_no_invented_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "greenfield"
            prepare(SKILL_ROOT, target, "greenfield")
            self.assertTrue((target / "docs/decision.md").is_file())
            self.assertFalse((target / "services").exists())
            self.assertFalse((target / "tests").exists())
            self.assertNotIn("python3", (target / "README.md").read_text())

    def test_merge_move_delete_preserve_load_and_repeat_is_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "maintenance"
            prepare(SKILL_ROOT, target, "maintenance")
            installed = target / "documents/rulers"
            note = (target / "notes.txt").read_bytes()
            receipt = (installed / "backend/RECEIPTS.md").read_bytes()
            candidate = target / ".rulers-work/revised"
            candidate.mkdir()
            (candidate / "INDEX.md").write_text("# Backend\n" + METADATA +
                "\nRefund: [PAYMENTS.md](PAYMENTS.md).\nReceipt: [RECEIPTS.md](RECEIPTS.md).\n")
            (candidate / "PAYMENTS.md").write_bytes((installed / "backend/REFUNDS.md").read_bytes())
            (candidate / "RECEIPTS.md").write_bytes(receipt)
            planpath = target / ".rulers-work/merge.json"
            self.call(target, "rules-plan", "--project-root", str(target), "--domain", "backend",
                      "--candidate-dir", candidate.relative_to(target).as_posix(), "--reason", "Synthetic merge and retirement",
                      "--activate-on-apply", "--output", str(planpath))
            self.call(target, "rules-apply", "--plan", str(planpath), *REVIEW)
            state = json.loads((installed / "RULERS_STATE.json").read_text())
            self.assertEqual({"INDEX.md", "PAYMENTS.md", "RECEIPTS.md"},
                             set(state["domains"]["backend"]["required_files"]))
            for name in ("REFUNDS", "RETRIES", "LOGGING"):
                self.assertFalse((installed / f"backend/{name}.md").exists())
            self.assertEqual(receipt, (installed / "backend/RECEIPTS.md").read_bytes())
            loaded = self.call(target, "--mode", "load", "--project-root", str(target),
                               "--domain", "backend", "--rule", "backend/PAYMENTS.md", "--format", "json", validator=True)
            self.assertIn("documents/rulers/backend/PAYMENTS.md", loaded["files"])
            self.assertFalse(any("rule-quality" in p for p in loaded["files"]))
            before = {str(p.relative_to(installed)): p.read_bytes() for p in installed.rglob("*")
                      if p.is_file() and not any(x in p.parts for x in (".plans", ".transactions"))}
            repeat = self.call(target, "rules-apply", "--plan", str(planpath), *REVIEW)
            self.assertEqual([], repeat["changed_files"])
            after = {str(p.relative_to(installed)): p.read_bytes() for p in installed.rglob("*")
                     if p.is_file() and not any(x in p.parts for x in (".plans", ".transactions"))}
            self.assertEqual(before, after)
            self.assertEqual(note, (target / "notes.txt").read_bytes())


if __name__ == "__main__":
    unittest.main()
