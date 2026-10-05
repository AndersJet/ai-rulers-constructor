"""Bind reviewed production-rule coverage without granting operation authority."""
from __future__ import annotations

import hashlib
import json
import re
import copy
from collections.abc import Mapping
from pathlib import PurePosixPath

from .domains import effective_dependency_configs, rule_owner


ROLES = ("security", "quality", "rollback")
_HASH = re.compile(r"sha256:[0-9a-f]{64}\Z")
_DECLARATION_FIELDS = {"version", "domain", "coverage", "profile_sha256", "bindings", "digest"}


class ReadinessError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def _digest(value):
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _valid_hash(value):
    return isinstance(value, str) and _HASH.fullmatch(value) is not None


def _safe_path(layout, relative):
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise ReadinessError("reference_invalid", "Readiness references must be project-relative rule paths")
    value = PurePosixPath(relative)
    if value.is_absolute() or ".." in value.parts or value.as_posix() != relative or value.suffix != ".md":
        raise ReadinessError("reference_invalid", "Readiness references must be canonical relative Markdown paths")
    if layout.project_root.resolve() != layout.project_root or layout.rulers_root.resolve() != layout.rulers_root:
        raise ReadinessError("reference_unsafe", "Project or rule root was redirected")
    path = layout.project_root / relative
    if not path.is_relative_to(layout.rulers_root):
        raise ReadinessError("reference_unsafe", "Readiness reference is outside the rules directory")
    current = layout.project_root
    for part in value.parts:
        current = current / part
        if current.is_symlink():
            raise ReadinessError("reference_unsafe", "Readiness references must not traverse symbolic links")
    return path


def _file_hash(path):
    if not path.is_file():
        raise ReadinessError("reference_missing", "An adopted readiness rule is missing")
    try:
        return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise ReadinessError("reference_unreadable", "An adopted readiness rule cannot be read") from exc


def _review_identity(value):
    if not isinstance(value, Mapping) or not all(
        isinstance(value.get(key), str) and value[key].strip()
        for key in ("reviewed_by", "reviewed_at", "evidence")
    ):
        raise ReadinessError("review_invalid", "Readiness requires a complete existing outer review")
    return {key: value[key] for key in ("reviewed_by", "reviewed_at", "evidence")}


def _active(config, owner):
    required_level = 1 if owner == "core" else 2
    if (config.get("retired") or type(config.get("level")) is not int
            or config["level"] < required_level or config.get("review_status") != "reviewed"):
        raise ReadinessError("owner_inactive", "A readiness rule owner is not active and reviewed")
    return _review_identity(config.get("review"))


def _profile_identity(layout, state):
    profile = state.get("profile")
    if not isinstance(profile, Mapping) or profile.get("status") != "reviewed":
        raise ReadinessError("profile_invalid", "Readiness requires a reviewed project profile")
    _review_identity(profile.get("review"))
    expected = profile.get("reviewed_sha256")
    if not _valid_hash(expected) or _file_hash(_safe_path(layout, f"{layout.rulers_dir}/PROJECT_PROFILE.md")) != expected:
        raise ReadinessError("profile_invalid", "Readiness profile identity does not match its review")
    return expected


def _source_paths(source):
    if not isinstance(source, Mapping) or set(source) != set(ROLES):
        raise ReadinessError("source_invalid", "Readiness source must contain only security, quality and rollback")
    result = {}
    for role in ROLES:
        paths = source[role]
        if not isinstance(paths, list) or not paths or any(not isinstance(path, str) or not path for path in paths):
            raise ReadinessError("source_invalid", "Each readiness role requires a nonempty list of rule paths")
        result[role] = sorted(set(paths))
    return result


def _candidate_rules(layout, configs, domain, candidate_hashes):
    if not isinstance(candidate_hashes, Mapping) or not candidate_hashes:
        raise ReadinessError("candidate_invalid", "Candidate hashes must name the complete target rule set")
    result = {}
    for relative, digest in candidate_hashes.items():
        path = _safe_path(layout, relative)
        ruler_relative = path.relative_to(layout.rulers_root).as_posix()
        if not _valid_hash(digest) or rule_owner(ruler_relative, configs) != domain:
            raise ReadinessError("candidate_invalid", "Readiness candidate crosses its target domain or has an invalid hash")
        result[relative] = digest
    return dict(sorted(result.items()))


def _adopted_rules(layout, state, configs, owner):
    config = configs[owner]
    filenames = config.get("required_files")
    if not isinstance(filenames, list) or not filenames or any(not isinstance(name, str) for name in filenames):
        raise ReadinessError("scope_invalid", "Readiness owner has no adopted rule inventory")
    inventory = state.get("managed_files")
    if not isinstance(inventory, Mapping):
        raise ReadinessError("scope_invalid", "Readiness requires an adopted managed inventory")
    rules = {}
    for filename in filenames:
        relative = f"{layout.rulers_dir}/{config.get('target_dir', owner)}/{filename}"
        path = _safe_path(layout, relative)
        if rule_owner(path.relative_to(layout.rulers_root).as_posix(), configs) != owner:
            raise ReadinessError("scope_invalid", "Readiness owner inventory crosses another rule domain")
        metadata = inventory.get(relative)
        if not isinstance(metadata, Mapping) or metadata.get("ownership") not in {"managed", "project-generated"}:
            raise ReadinessError("reference_unadopted", "Readiness reference is outside adopted inventory")
        expected = metadata.get("rendered_sha256")
        if not _valid_hash(expected) or _file_hash(path) != expected:
            raise ReadinessError("reference_drift", "Readiness rule identity differs from its adopted hash")
        rules[relative] = expected
    return dict(sorted(rules.items()))


def compile_readiness(layout, state, domain, source, *, candidate_hashes=None, candidate_texts=None):
    """Compile coverage for one approval; candidate hashes describe its full target.

    All paths are canonical project-relative paths beneath the configured rulers
    root. This reads identities and reviews only; it never writes or executes a
    validation command. The caller stores the result in the approved outer review.
    """
    paths = _source_paths(source)
    if not isinstance(state, Mapping):
        raise ReadinessError("scope_invalid", "Readiness requires a project State")
    if candidate_hashes is not None and domain in state.get("domains", {}):
        state = copy.deepcopy(state)
        target = state["domains"][domain]
        prefix = f"{layout.rulers_dir}/{target.get('target_dir', domain)}/"
        target["required_files"] = [path.removeprefix(prefix) for path in candidate_hashes]
        target["generated"] = True
        for path, digest in candidate_hashes.items():
            state.setdefault("managed_files", {})[path] = {"ownership": "managed", "rendered_sha256": digest}
    try:
        dependency_errors = []
        configs = effective_dependency_configs({}, state, layout, rule_text_overrides=candidate_texts, errors=dependency_errors)
    except ValueError as exc:
        raise ReadinessError("scope_invalid", str(exc)) from exc
    if not isinstance(domain, str) or domain not in configs or domain == "core":
        raise ReadinessError("scope_invalid", "Readiness target must be an adopted non-core domain")
    profile_hash = _profile_identity(layout, state)
    target_rules = (_candidate_rules(layout, configs, domain, candidate_hashes) if candidate_hashes is not None
                    else _adopted_rules(layout, state, configs, domain))
    owner_rules = {domain: target_rules}
    owners = {domain}
    coverage = {}
    for role, references in paths.items():
        coverage[role] = []
        for relative in references:
            path = _safe_path(layout, relative)
            owner = rule_owner(path.relative_to(layout.rulers_root).as_posix(), configs)
            if owner not in configs:
                raise ReadinessError("reference_unadopted", "Readiness reference has no adopted rule owner")
            if owner not in owner_rules:
                _active(configs[owner], owner)
                owner_rules[owner] = _adopted_rules(layout, state, configs, owner)
            if relative not in owner_rules[owner]:
                raise ReadinessError("reference_unadopted", "Readiness reference is outside the approved rule set")
            owners.add(owner)
            coverage[role].append({"path": relative, "sha256": owner_rules[owner][relative]})

    dependencies = {}
    visiting, visited = set(), set()

    def include(owner):
        if owner in visiting:
            raise ReadinessError("dependency_invalid", "Readiness declared dependencies contain a cycle")
        if owner in visited:
            return
        visiting.add(owner)
        declared = configs[owner].get("requires_active", [])
        if not isinstance(declared, list) or any(not isinstance(name, str) or name not in configs for name in declared):
            raise ReadinessError("dependency_invalid", "Readiness owner has an invalid declared dependency")
        dependencies[owner] = sorted(set(declared))
        for required in dependencies[owner]:
            include(required)
        visiting.remove(owner)
        visited.add(owner)

    for owner in sorted(owners):
        include(owner)
    for error in dependency_errors:
        if error.domain is None or error.domain in visited:
            raise ReadinessError("dependency_invalid", str(error))
    bindings = {}
    for owner in sorted(visited):
        if owner != domain:
            _active(configs[owner], owner)
        rules = owner_rules.get(owner)
        if rules is None:
            rules = _adopted_rules(layout, state, configs, owner)
        bindings[owner] = {"target_dir": configs[owner].get("target_dir", owner), "rules": rules,
                           "requires_active": dependencies[owner]}
    declaration = {"version": 1, "domain": domain, "coverage": coverage,
                   "profile_sha256": profile_hash, "bindings": bindings}
    return {**declaration, "digest": _digest(declaration)}


def _declaration_source(declaration, domain):
    if not isinstance(declaration, Mapping) or set(declaration) != _DECLARATION_FIELDS:
        raise ReadinessError("declaration_invalid", "Readiness declaration has an invalid shape")
    if type(declaration["version"]) is not int or declaration["version"] != 1 or declaration["domain"] != domain:
        raise ReadinessError("declaration_invalid", "Readiness declaration protocol or target is invalid")
    if not _valid_hash(declaration["digest"]) or declaration["digest"] != _digest({
        key: value for key, value in declaration.items() if key != "digest"
    }):
        raise ReadinessError("declaration_invalid", "Readiness approval binding digest does not match")
    coverage = declaration["coverage"]
    if not isinstance(coverage, Mapping) or set(coverage) != set(ROLES):
        raise ReadinessError("declaration_invalid", "Readiness coverage roles are invalid")
    source = {}
    for role in ROLES:
        refs = coverage[role]
        if not isinstance(refs, list) or not refs or any(
            not isinstance(ref, Mapping) or set(ref) != {"path", "sha256"}
            or not isinstance(ref["path"], str) or not _valid_hash(ref["sha256"]) for ref in refs
        ):
            raise ReadinessError("declaration_invalid", "Readiness coverage references are invalid")
        source[role] = [ref["path"] for ref in refs]
    if not isinstance(declaration["bindings"], Mapping):
        raise ReadinessError("declaration_invalid", "Readiness owner bindings are invalid")
    return source


def evaluate_readiness(inspection, domain):
    """Return advisory evidence status without altering task or validation state."""
    state = inspection.state or {}
    domains = state.get("domains", {}) if isinstance(state, Mapping) else None
    target = domains.get(domain, {}) if isinstance(domains, Mapping) else None
    if not isinstance(target, Mapping):
        return {"ready": False, "status": "unmet", "reasons": ["scope_invalid"]}
    review = target.get("review") or {}
    declaration = review.get("readiness") if isinstance(review, Mapping) else None
    if declaration is None:
        if isinstance(review, Mapping) and "readiness_approval" in review:
            return {"ready": False, "status": "unmet", "reasons": ["approval_unbound"]}
        return {"ready": False, "status": "not_assessed", "reasons": ["no_declaration"]}
    reasons = []
    if inspection.global_blocked:
        reasons.append("global_blocked")
    if not inspection.profile_valid:
        reasons.append("profile_invalid")
    if domain in inspection.invalid_domains:
        reasons.append("scope_invalid")
    if reasons:
        return {"ready": False, "status": "unmet", "reasons": reasons}
    try:
        _active(target, domain)
        source = _declaration_source(declaration, domain)
        approval = review.get("readiness_approval")
        if approval is not None:
            if (not isinstance(approval, Mapping) or set(approval) != {
                    "scope", "reviewed_by", "reviewed_at", "evidence", "plan_sha256", "declaration_digest"}
                    or approval["scope"] != "readiness" or not _valid_hash(approval["plan_sha256"])
                    or approval["declaration_digest"] != declaration["digest"]):
                raise ReadinessError("approval_unbound", "Readiness approval does not bind this declaration")
            _review_identity(approval)
        if set(declaration["bindings"]) & set(inspection.invalid_domains):
            raise ReadinessError("owner_invalid", "A bound readiness rule owner is invalid")
        current = compile_readiness(inspection.layout, state, domain, source)
        if current != declaration:
            raise ReadinessError("binding_changed", "Readiness coverage or approval inputs changed")
    except (ReadinessError, OSError, TypeError, KeyError, ValueError) as exc:
        code = exc.code if isinstance(exc, ReadinessError) else "declaration_invalid"
        return {"ready": False, "status": "unmet", "reasons": [code]}
    return {"ready": True, "status": "ready", "reasons": []}
