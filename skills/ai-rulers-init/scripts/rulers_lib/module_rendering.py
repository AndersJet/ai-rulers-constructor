"""Project portable module rules into the main workspace without copying its framework."""
from __future__ import annotations

import json
import posixpath
import re
from urllib.parse import urlsplit

from .module_contracts import json_bytes


def storage_prefix(rulers_dir: str, name: str) -> str:
    # Percent escapes are decoded by Markdown link resolution. Use a disjoint,
    # filesystem-safe namespace for Git names containing separators or punctuation.
    folder = name if re.fullmatch(r"[A-Za-z0-9_-]+", name) else "~"+name.encode("utf-8").hex()
    return f"{rulers_dir}/modules/{folder}/effective"


def render_module(snapshot: dict, *, name: str, code_root: str, rulers_dir: str, adjustments=None) -> dict[str, bytes]:
    prefix = storage_prefix(rulers_dir, name)
    source_rules = snapshot["source"]["rulers_dir"]
    from .module_adjustments import effective_export, empty_adjustments
    rules = effective_export(snapshot,adjustments or empty_adjustments())["rules"]

    def reference(source: str, value: str) -> str:
        raw = value.strip().strip('"\'')
        if raw.startswith("#") or urlsplit(raw).scheme:
            return value
        path, marker, anchor = raw.partition("#")
        if path in {"AGENTS.md", "CLAUDE.md", "RULERS_STATE.json"}:
            destination = f"{rulers_dir}/AGENTS.md"
        elif path == "PROJECT_PROFILE.md":
            destination = prefix + "/PROFILE.md"
        else:
            absolute = posixpath.normpath(path if path.startswith(source_rules + "/") else posixpath.join(source_rules, posixpath.dirname(source), path))
            if absolute.startswith("../") or absolute.startswith("/"):
                raise ValueError("Portable reference escapes module code root")
            if absolute.startswith(source_rules + "/"):
                relative = absolute[len(source_rules) + 1:]
                if relative in rules:
                    destination = prefix + "/rules/" + relative
                elif relative in {"AGENTS.md", "CLAUDE.md", "RULERS_STATE.json"}:
                    destination = rulers_dir + "/AGENTS.md"
                elif relative == "PROJECT_PROFILE.md":
                    destination = prefix + "/PROFILE.md"
                elif relative in {"core/HARD_CONSTRAINTS.md", "core/WORKFLOW.md", "core/DOC_GOVERNANCE.md", "core/RULER_MAINTENANCE.md"}:
                    destination = rulers_dir + "/" + relative
                else:
                    raise ValueError(f"Rule dependency is not exported: {relative}")
            else:
                destination = posixpath.relpath(code_root + "/" + absolute, posixpath.dirname(prefix+"/rules/"+source))
        return destination + (marker + anchor if marker else "")

    result = {prefix + "/source.json": json_bytes(snapshot),
              prefix + "/PROFILE.md": snapshot["profile"].encode("utf-8")}
    for relative, rule in rules.items():
        text = re.sub(r"\[([^\]]*)\]\(([^)]+)\)", lambda m: f"[{m[1]}]({reference(relative,m[2])})", rule["text"])
        text = re.sub(r"`([^`\n]+\.(?:md|json)(?:#[^`\n]*)?)`", lambda m: "`"+reference(relative,m[1])+"`", text)
        lines = []
        section = None
        for line in text.splitlines():
            if line.strip() in {"applies_to:", "must_load_with:"}:
                section = line.strip().rstrip(":")
            elif section and line.strip().startswith("- "):
                value = line.strip()[2:].strip().strip('"\'')
                rewritten = code_root + "/" + value if section == "applies_to" else reference(relative,value)
                line = line[:len(line)-len(line.lstrip())] + "- " + json.dumps(rewritten,ensure_ascii=False)
            elif line.strip():
                section = None
            lines.append(line)
        result[prefix + "/rules/" + relative] = ("\n".join(lines)+"\n").encode("utf-8")
    return result
