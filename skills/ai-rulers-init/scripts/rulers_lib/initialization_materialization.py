"""Derive execution bytes from the reviewed plan, varying only approval metadata."""

import base64
import copy
import json

from .module_contracts import content_hash, identity, json_bytes

PENDING_REVIEW = {
    "reviewed_by": "pending-review",
    "evidence": "pending-review",
    "reviewed_at": "1970-01-01T00:00:00+00:00",
}


def _record_approval(value, review):
    if isinstance(value, dict):
        if all(value.get(key) == expected for key, expected in PENDING_REVIEW.items()):
            value.update(review)
        for child in value.values():
            _record_approval(child, review)
    elif isinstance(value, list):
        for child in value:
            _record_approval(child, review)


def approved_changes(plan, review):
    changes = copy.deepcopy(plan["changes"])
    states = {}
    source_state_hashes = {}
    for name, scope in changes.items():
        state_path = scope["rulers_dir"] + "/RULERS_STATE.json"
        encoded = scope["files"].get(state_path)
        if encoded is None:
            continue
        state = json.loads(base64.b64decode(encoded, validate=True))
        _record_approval(state, review)
        content = json_bytes(state)
        scope["files"][state_path] = base64.b64encode(content).decode()
        source_state_hashes[scope["path"]] = (state_path, content_hash(content))
        states[name] = (state_path, state)

    root_scope = plan["root_scope"]
    if root_scope not in states:
        return changes
    state_path, state = states[root_scope]
    files = changes[root_scope]["files"]
    for record in state.get("modules", {}).values():
        source_path = record["source"]["path"]
        packet_path = record.get("snapshot", {}).get("source_file")
        if (
            source_path not in source_state_hashes
            or not packet_path
            or packet_path not in files
        ):
            continue  # An unchanged accepted snapshot keeps its original provenance.
        packet = json.loads(base64.b64decode(files[packet_path], validate=True))
        source_state_path, digest = source_state_hashes[source_path]
        if source_state_path not in packet["source"]["input_hashes"]:
            raise ValueError("Reviewed snapshot is missing its source State binding")
        packet["source"]["input_hashes"][source_state_path] = digest
        packet["capture_id"] = identity(
            {key: value for key, value in packet.items() if key != "capture_id"}
        )
        content = json_bytes(packet)
        files[packet_path] = base64.b64encode(content).decode()
        record["snapshot"]["capture_id"] = packet["capture_id"]
        state["managed_files"][packet_path].update(
            source_sha256=content_hash(content), rendered_sha256=content_hash(content)
        )
    files[state_path] = base64.b64encode(json_bytes(state)).decode()
    return changes


def verify_execution(plan, execution, reviewed_by, evidence):
    review = execution.get("review")
    if not isinstance(review, dict) or set(review) != set(PENDING_REVIEW):
        raise ValueError("Execution review does not match the reviewed plan")
    if review["reviewed_by"] != reviewed_by or review["evidence"] != evidence:
        raise ValueError("Resume requires the original reviewer and evidence")
    from datetime import datetime

    if not isinstance(review["reviewed_at"], str):
        raise ValueError("Execution review timestamp must be an ISO timestamp")
    datetime.fromisoformat(review["reviewed_at"])
    if (
        execution.get("changes") != approved_changes(plan, review)
        or execution.get("preparation") != plan["preparation"]
    ):
        raise ValueError("Execution content differs from the reviewed plan")
