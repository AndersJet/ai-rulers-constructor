#!/usr/bin/env python3
"""Run one natural-task CLI replay, retaining public events and snapshots.

No bypass flags, model answers or grading criteria are injected. Input answers
must already have provenance; this runner is not an interactive human simulator.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path

from scripts.prepare_interop_eval import snapshot


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--prompt", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--model", help="Omit to preserve the configured host default.")
    parser.add_argument("--timeout", type=int, default=900)
    args = parser.parse_args()
    target, evidence = args.target.resolve(), args.evidence.resolve()
    if evidence.exists():
        raise ValueError(f"Refusing to overwrite evidence: {evidence}")
    evidence.mkdir(parents=True)
    prompt = args.prompt.read_bytes()
    (evidence / "prompt.txt").write_bytes(prompt)
    command = ["codex", "exec", "--cd", str(target), "--sandbox", "workspace-write",
               "--json", "--output-last-message", str(evidence / "last-message.txt"), "-"]
    if args.model:
        command[2:2] = ["--model", args.model]
    version = subprocess.run(["codex", "--version"], capture_output=True, text=True)
    manifest = {"host": "Codex CLI", "cli_version": version.stdout.strip(),
                "requested_model": args.model or "configured-host-default",
                "resolved_model": "unknown-unless-public-events-report-it",
                "reasoning": "configured-host-default-unverified", "command": command,
                "prompt_sha256": hashlib.sha256(prompt).hexdigest(), "before": snapshot(target),
                "started_at_unix": time.time(), "live_hitl": False}
    with (evidence / "events.jsonl").open("wb") as events, (evidence / "stderr.txt").open("wb") as stderr:
        try:
            result = subprocess.run(command, input=prompt, stdout=events, stderr=stderr,
                                    cwd=target, timeout=args.timeout)
            manifest["exit_code"] = result.returncode
        except subprocess.TimeoutExpired:
            manifest["exit_code"] = None
            manifest["failure"] = "executor-timeout; partial events retained"
    manifest["finished_at_unix"] = time.time()
    manifest["after"] = snapshot(target)
    (evidence / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"evidence": str(evidence), "exit_code": manifest["exit_code"]}))


if __name__ == "__main__":
    main()
