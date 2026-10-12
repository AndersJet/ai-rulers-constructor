from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path, PurePosixPath
from typing import AbstractSet, Any, Mapping


class DependencyContractError(ValueError):
    """An unsafe or invalid dependency, with the owning scope when known."""

    def __init__(self, message: str, *, domain: str | None = None, path: str | None = None):
        super().__init__(message)
        self.domain = self.scope = domain
        self.path = path


def load_domain_registry(skill_root: Path) -> dict[str, dict[str, Any]]:
    path = skill_root / "templates" / "domain-registry.json"
    return json.loads(path.read_text(encoding="utf-8"))["domains"]


def detect_domains(project_root: Path, registry: dict[str, dict[str, Any]]) -> list[str]:
    detected: list[str] = []
    for domain, config in registry.items():
        if domain == "core":
            continue
        hints = config.get("detection_hints", [])
        if any((project_root / hint).exists() for hint in hints):
            detected.append(domain)
    return sorted(detected)


def effective_domain_configs(registry: Mapping, state: Mapping) -> dict[str, Mapping]:
    """Keep registry namespace reservations and use installed target overrides."""
    installed = state.get("domains", {})
    if not isinstance(installed, Mapping):
        raise DependencyContractError("Installed domain contracts must be objects")
    result = {name: dict(config) for name, config in registry.items()}
    for name, config in installed.items():
        if not isinstance(config, Mapping):
            raise DependencyContractError(f"Domain '{name}' contract must be an object", domain=name)
        result[name] = {**result.get(name, {}), **config}
        if "requires_active" not in config:
            # Through 4.0.4 the validator imposed this without a recorded edge.
            # New installations always record requires_active explicitly.
            result[name]["requires_active"] = ["security"] if name == "delivery" else []
    for name, config in result.items():
        if "requires_active" not in config:
            raise DependencyContractError(f"Domain '{name}' requires_active is missing", domain=name)
    return result


def effective_dependency_configs(
    registry: Mapping, state: Mapping, layout, *, rule_text_overrides: Mapping[str, str] | None = None,
    errors: list[DependencyContractError] | None = None,
) -> dict[str, Mapping]:
    """Derive declared and adopted metadata dependencies; navigation is not an edge.

    Runtime callers pass an empty registry. Candidate callers may supply texts keyed
    by project-relative adopted paths together with their candidate State inventory.
    """
    from .paths import resolve_safe_child
    from .rule_loading import references, resolve_reference

    def report(error: DependencyContractError) -> None:
        if errors is None:
            raise error
        errors.append(error)

    configs = effective_domain_configs(registry, state)
    edges: dict[str, set[str]] = {}
    for name, config in configs.items():
        requirements = config["requires_active"]
        if isinstance(requirements, (str, bytes)) or not isinstance(requirements, Sequence):
            report(DependencyContractError(f"Domain '{name}' requires_active must be a list", domain=name))
            requirements = []
        if any(not isinstance(target, str) or not target or target not in configs for target in requirements):
            report(DependencyContractError(f"Domain '{name}' has an unknown dependency", domain=name))
        if all(isinstance(target, str) for target in requirements) and len(requirements) != len(set(requirements)):
            report(DependencyContractError(f"Domain '{name}' duplicates dependencies", domain=name))
        edges[name] = {target for target in requirements if isinstance(target, str) and target in configs}

    installed = state.get("domains", {})
    inventory = state.get("managed_files", {})
    if not isinstance(inventory, Mapping):
        raise DependencyContractError("Managed rule inventory must be an object")
    adopted: dict[str, str] = {}
    for name, config in installed.items():
        if not (config.get("generated") or type(config.get("level")) is int and config["level"] >= 2):
            continue
        names = config.get("required_files", [])
        if isinstance(names, (str, bytes)) or not isinstance(names, Sequence):
            report(DependencyContractError(f"Domain '{name}' required_files must be a list", domain=name))
            continue
        for filename in names:
            if not isinstance(filename, str) or not filename.endswith(".md"):
                report(DependencyContractError(f"Domain '{name}' has an invalid adopted rule", domain=name))
                continue
            relative = f"{config.get('target_dir', name)}/{filename}"
            path = f"{layout.rulers_dir}/{relative}"
            try:
                resolve_safe_child(layout.rulers_root, relative)
                if rule_owner(relative, configs) != name:
                    raise ValueError("Rule belongs to another domain")
            except ValueError as exc:
                report(DependencyContractError(str(exc), domain=name, path=path))
                continue
            if path not in (rule_text_overrides or {}) and not (layout.project_root / path).is_file():
                # Existing missing-file diagnostics belong to this owner; no
                # metadata can be read or trusted from an absent adopted file.
                continue
            metadata = inventory.get(path)
            if not isinstance(metadata, Mapping) or metadata.get("ownership") not in {"managed", "project-generated"}:
                report(DependencyContractError(f"Rule is outside adopted inventory: {path}", domain=name, path=path))
                continue
            adopted[path] = name

    protocol = {"AGENTS.md", "CLAUDE.md", f"{layout.rulers_dir}/AGENTS.md",
                f"{layout.rulers_dir}/RULERS_STATE.json", f"{layout.rulers_dir}/PROJECT_PROFILE.md",
                f"{layout.rulers_dir}/core/HARD_CONSTRAINTS.md", f"{layout.rulers_dir}/core/WORKFLOW.md"}
    overrides = rule_text_overrides or {}
    for relative, name in adopted.items():
        try:
            source = resolve_safe_child(layout.project_root, relative)
            if relative in overrides:
                text = overrides[relative]
            elif source.is_file():
                text = source.read_text(encoding="utf-8")
            else:
                # Inspection separately marks this owner invalid. Its declared
                # edges and inbound metadata edges remain available for propagation.
                continue
            dependencies, _ = references(text)
            for value in dependencies:
                from urllib.parse import unquote, urlsplit
                local = unquote(value.strip().strip('"\'<>').split("#", 1)[0])
                if not urlsplit(local).scheme:
                    if Path(local).is_absolute():
                        raise ValueError("Dependency path must be project-relative")
                    cursor = layout.project_root if local.startswith(layout.rulers_dir + "/") or local in {"AGENTS.md", "CLAUDE.md"} else source.parent
                    for part in Path(local).parts:
                        cursor = cursor.parent if part == ".." else cursor / part
                        if not cursor.is_relative_to(layout.project_root) or cursor.is_symlink():
                            raise ValueError("Dependency path escapes or crosses a symbolic link")
                    resolve_safe_child(layout.project_root, cursor.relative_to(layout.project_root))
                target = resolve_reference(layout, source, value)
                if target is None:
                    raise ValueError("must_load_with must reference a local adopted rule")
                dependency = target.relative_to(layout.project_root).as_posix()
                resolve_safe_child(layout.project_root, dependency)
                if dependency in protocol:
                    continue
                owner = adopted.get(dependency)
                if owner is None:
                    raise ValueError(f"Dependency is outside adopted inventory: {dependency}")
                if owner != name:
                    edges[name].add(owner)
        except (OSError, UnicodeError, ValueError) as exc:
            report(DependencyContractError(str(exc), domain=name, path=relative))

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(name: str, chain: tuple[str, ...]) -> None:
        if name in visiting:
            report(DependencyContractError("Dependency cycle: " + " -> ".join((*chain, name)), domain=name))
            return
        if name in visited:
            return
        visiting.add(name)
        for target in sorted(edges[name]):
            visit(target, (*chain, name))
        visiting.remove(name)
        visited.add(name)

    for name in sorted(edges):
        visit(name, ())
    return {name: {**config, "requires_active": sorted(edges[name])} for name, config in configs.items()}


def rule_owner(relative: str, domains: Mapping[str, Mapping]) -> str | None:
    """The most specific domain directory owns a rulers-relative file."""
    path = PurePosixPath(relative)
    matches = []
    for name, config in domains.items():
        target = PurePosixPath(config.get("target_dir", name))
        if target in path.parents:
            matches.append((len(target.parts), name))
    if not matches:
        return None
    depth = max(length for length, _ in matches)
    owners = [name for length, name in matches if length == depth]
    if len(owners) != 1:
        raise ValueError(f"Ambiguous rule ownership: {relative}")
    return owners[0]


def nested_domain_dirs(domain: str, domains: Mapping[str, Mapping]) -> tuple[str, ...]:
    root = PurePosixPath(domains[domain].get("target_dir", domain))
    return tuple(sorted({str(PurePosixPath(config.get("target_dir", other)).relative_to(root))
        for other, config in domains.items()
        if other != domain and root in PurePosixPath(config.get("target_dir", other)).parents}))


def expand_reverse_dependencies(
    domains: AbstractSet[str],
    registry: Mapping[str, Mapping[str, Any]],
) -> frozenset[str]:
    for domain, config in registry.items():
        if "requires_active" not in config:
            raise ValueError(f"Domain '{domain}' requires_active is missing.")
        requirements = config["requires_active"]
        if isinstance(requirements, (str, bytes)) or not isinstance(
            requirements, Sequence
        ):
            raise ValueError(
                f"Domain '{domain}' requires_active must be a sequence of domain names."
            )
        if any(not isinstance(required, str) for required in requirements):
            raise ValueError(
                f"Domain '{domain}' requires_active must contain only domain names."
            )
        unknown = [required for required in requirements if required not in registry]
        if unknown:
            raise ValueError(
                f"Domain '{domain}' requires_active references unknown domains: "
                + ", ".join(unknown)
            )

    expanded = set(domains)
    while True:
        dependents = {
            domain
            for domain, config in registry.items()
            if domain not in expanded
            and any(required in expanded for required in config.get("requires_active", ()))
        }
        if not dependents:
            return frozenset(expanded)
        expanded.update(dependents)
