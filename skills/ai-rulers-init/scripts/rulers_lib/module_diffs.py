"""Review projection; unchanged rule bodies stay out of the change report."""
from difflib import unified_diff


def review_changes(before, after):
    before = before or {}
    old_rules = before.get("rules", {})
    new_rules = after["rules"]
    rules = {}
    for path in sorted(old_rules.keys() | new_rules.keys()):
        old, new = old_rules.get(path), new_rules.get(path)
        if old == new:
            continue
        rules[path] = {
            "operation": "add" if old is None else "delete" if new is None else "modify",
            "domain_before": old.get("domain") if old else None,
            "domain_after": new.get("domain") if new else None,
            "diff": "".join(unified_diff((old or {}).get("text", "").splitlines(keepends=True),
                (new or {}).get("text", "").splitlines(keepends=True),fromfile="accepted/"+path,tofile="candidate/"+path)),
        }
    facts = {key: {"before": before.get(key), "after": after.get(key)}
             for key in ("profile", "commands", "evidence", "core_decisions", "profile_scopes")
             if before.get(key) != after.get(key)}
    return {"rules": rules, "facts": facts}
