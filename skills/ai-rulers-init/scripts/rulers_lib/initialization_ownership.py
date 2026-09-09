"""Find structural overlap; semantic ownership decisions remain explicit review input."""

from pathlib import Path
import re

from .module_contracts import checked_path, identity


def overlaps(root, rulers_dir, state, module, snapshot, resolutions, accepted):
    pending = []
    selected = []
    rules = {}
    for domain, config in state.get("domains", {}).items():
        if config.get("level", 0) < 2:
            continue
        for file in config.get("required_files", []):
            relative = config["target_dir"] + "/" + file
            if Path(relative).name == "INDEX.md":
                continue
            path = checked_path(root, rulers_dir + "/" + relative, required=True)
            rules[relative] = (domain, path.read_text(encoding="utf-8"))

    def body(text):
        return re.sub(r"\s+", " ", re.sub(r"```yaml[\s\S]*?```", "", text)).strip()

    for workspace_rule, (domain, text) in rules.items():
        for module_rule, rule in snapshot["rules"].items():
            if rule["domain"] != domain or Path(module_rule).name == "INDEX.md":
                continue
            duplicate = body(text) == body(rule["text"])
            if not duplicate and Path(workspace_rule).name != Path(module_rule).name:
                continue
            binding = {
                "module": module,
                "workspace_rule": workspace_rule,
                "module_rule": module_rule,
            }
            key = identity(
                {**binding, "workspace_text": text, "module_text": rule["text"]}
            )
            requested = next(
                (
                    r
                    for r in resolutions
                    if all(r.get(k) == v for k, v in binding.items())
                ),
                None,
            )
            decision = requested or accepted.get(key)
            if (
                decision
                and decision.get("decision") == "keep-scoped"
                and isinstance(decision.get("reason"), str)
                and decision["reason"].strip()
            ):
                selected.append(
                    (
                        key,
                        {
                            **binding,
                            "decision": "keep-scoped",
                            "reason": decision["reason"],
                        },
                    )
                )
            else:
                pending.append(
                    {
                        **binding,
                        "kind": "duplicate" if duplicate else "possible-conflict",
                        "reason": "ownership review required: revise candidates to remove overlap or explicitly keep scoped rules",
                        "suggestion": "Keep portable constraints in module sources; keep composition constraints in the workspace",
                    }
                )
    return pending, selected
