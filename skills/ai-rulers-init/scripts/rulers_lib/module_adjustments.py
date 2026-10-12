"""Explicit workspace adjustments with source-hash conflict bindings."""
from __future__ import annotations

import copy
import posixpath
import re
from pathlib import Path

from .module_contracts import checked_path, read_json, file_identity, identity
from .validation import validate_rule_metadata_text, TEMPLATE_RESIDUE_PATTERNS


def empty_adjustments():
    return {"replace":{},"add":{},"disable":[],"base_hashes":{}}


def validate_adjustment_definition(definition):
    if set(definition)-{"replace","add","disable"}:
        raise ValueError("Unknown workspace adjustment fields")
    for kind in ("replace", "add"):
        if not isinstance(definition.get(kind, {}), dict):
            raise ValueError(f"{kind} must be an object mapping rule paths to adjustments")
    if not isinstance(definition.get("disable", []), list) or not all(isinstance(x, str) for x in definition.get("disable", [])):
        raise ValueError("disable must be a list of source rule paths")
    for kind in ("replace", "add"):
        for name, value in definition.get(kind, {}).items():
            if kind == "add" and (not isinstance(value, dict) or set(value) != {"path", "domain"}
                    or not isinstance(value.get("domain"), str) or not re.fullmatch(r"[A-Za-z0-9_-]+", value["domain"])):
                raise ValueError(f"add.{name} requires path and a valid domain identity")
            source = value if kind == "replace" else value["path"]
            if not isinstance(source, str) or not source:
                raise ValueError(f"{kind}.{name} requires a workspace-relative Markdown file path")


def read_adjustments(root: Path, path: str, snapshot: dict):
    manifest = checked_path(root,path,required=True)
    inputs = {path:file_identity(manifest)}
    definition = read_json(manifest)
    validate_adjustment_definition(definition)
    result = empty_adjustments()
    for name in definition.get("disable",[]):
        if name not in snapshot["rules"]:
            raise ValueError(f"Cannot disable unknown source rule: {name}")
        result["disable"].append(name)
    for kind in ("replace","add"):
        for name, value in definition.get(kind,{}).items():
            if not name.endswith(".md") or ".." in Path(name).parts or Path(name).is_absolute():
                raise ValueError("Adjustment rule identity must be a safe Markdown path")
            if (kind=="replace") != (name in snapshot["rules"]):
                raise ValueError(f"Choose replace for existing rules and add for new rules: {name}")
            source = value if kind=="replace" else value["path"]
            file = checked_path(root,source,required=True)
            text = file.read_text(encoding="utf-8")
            if validate_rule_metadata_text(text,name) or any(p.search(text) for _,p,_ in TEMPLATE_RESIDUE_PATTERNS):
                raise ValueError(f"Invalid adjustment rule: {name}")
            inputs[source] = file_identity(file)
            domain = snapshot["rules"][name]["domain"] if kind=="replace" else value["domain"]
            result[kind][name] = {"domain":domain,"text":text}
    if set(result["disable"]) & set(result["replace"]):
        raise ValueError("A rule cannot be replaced and disabled together")
    for name in set(result["disable"]) | set(result["replace"]):
        result["base_hashes"][name] = identity(snapshot["rules"][name])
    result["disable"] = sorted(set(result["disable"]))
    if any(file_identity(checked_path(root,p,required=True)) != digest for p,digest in inputs.items()):
        raise ValueError("Adjustments changed while reading; retry")
    return result,inputs


def adjustment_conflicts(snapshot,adjustments):
    conflicts = []
    for name, expected in adjustments.get("base_hashes",{}).items():
        current = snapshot["rules"].get(name)
        if current is None or identity(current) != expected:
            conflicts.append({"rule":name,"reason":"source-changed-under-adjustment"})
    for name in adjustments.get("add",{}):
        if name in snapshot["rules"]:
            conflicts.append({"rule":name,"reason":"source-now-defines-added-rule"})
    return conflicts


def effective_export(snapshot,adjustments):
    result = copy.deepcopy(snapshot)
    disabled = set(adjustments.get("disable",[]))
    for name in disabled:
        result["rules"].pop(name,None)
    result["rules"].update(adjustments.get("replace",{}))
    result["rules"].update(adjustments.get("add",{}))
    source_root = snapshot["source"]["rulers_dir"]
    def is_disabled(source,value):
        target = value.split("#",1)[0]
        if target.startswith(source_root+"/"):
            relative = target[len(source_root)+1:]
        else:
            relative = posixpath.normpath(posixpath.join(posixpath.dirname(source),target))
        return relative in disabled
    for name,rule in result["rules"].items():
        if Path(name).name != "INDEX.md":
            continue
        text = re.sub(r"\[([^\]]*)\]\(([^)]+)\)",
                      lambda m: m[1]+"（本工作区停用）" if is_disabled(name,m[2]) else m[0],rule["text"])
        rule["text"] = re.sub(r"`([^`\n]+\.md)`",lambda m: "本工作区停用" if is_disabled(name,m[1]) else m[0],text)
    return result
