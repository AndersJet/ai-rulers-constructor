"""Validate every participating scope, including read-only module sources."""

import base64

from .initialization_projection import snapshot
from .module_contracts import checked_path, identity, content_hash
from .paths import resolve_layout
from .transactions import inspect_incomplete_transaction, restore_transaction


def execution_scope(plan, name, change):
    expected = plan["scopes"][name]
    if (
        change["path"] != expected["path"]
        or change["rulers_dir"] != expected["rulers_dir"]
        or set(change["files"]) != set(plan["changes"][name]["files"])
    ):
        raise ValueError("Execution scope differs from reviewed initialization plan")
    before = expected["inputs"]
    after = dict(before)
    for path, value in change["files"].items():
        if value is None:
            after.pop(path, None)
        else:
            after[path] = content_hash(base64.b64decode(value, validate=True))
    return before, after


def verify_scopes(plan, execution, root, *, recover=False):
    if set(execution["changes"]) != set(plan["changes"]):
        raise ValueError("Initialization execution targets changed")
    for name, scope in plan["scopes"].items():
        project = checked_path(root, scope["path"]) if scope["path"] else root
        if recover:
            layout = resolve_layout(project, scope["rulers_dir"])
            incomplete = inspect_incomplete_transaction(layout)
            if incomplete:
                txn_id = identity({"plan": plan["digest"], "scope": name})[7:23]
                if (
                    name not in execution["changes"]
                    or incomplete.transaction_id != txn_id
                ):
                    raise ValueError("Unrelated transaction requires separate repair")
                restore_transaction(
                    layout=layout,
                    transaction_id=txn_id,
                    expected_lock_sha256=incomplete.lock_sha256,
                    expected_lock_nonce=incomplete.lock_nonce,
                )
    for name, scope in plan["scopes"].items():
        project = root / scope["path"]
        excluded = (
            [m["git"]["path"] for m in plan["modules"].values()]
            if name == plan["root_scope"]
            else []
        )
        actual = snapshot(project, excluded)
        before = scope["inputs"]
        allowed = [before]
        if name in execution["changes"]:
            allowed = list(execution_scope(plan, name, execution["changes"][name]))
        if actual not in allowed:
            raise ValueError(
                "Project inputs changed: " + name + "; preserve work and replan"
            )
