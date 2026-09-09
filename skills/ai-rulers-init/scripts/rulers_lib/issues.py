from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    path: str | None = None
    severity: str = "error"
    scope: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return asdict(self)

    def context_dict(self) -> dict[str, str | None]:
        """Compact representation for Context output: code and scope only."""
        return {"code": self.code, "scope": self.scope}
