from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path, PurePosixPath
from typing import AbstractSet, Any, Mapping


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
    return {name: {**config, **state.get("domains", {}).get(name, {})}
            for name, config in registry.items()} | {
                name: config for name, config in state.get("domains", {}).items()
                if name not in registry
            }


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
