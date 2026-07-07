"""AgentResult — what every agent execution returns."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentResult:
    """The outcome of a single agent execution.

    *success*     — ``True`` if the agent completed without error.
    *output*      — structured data produced by the agent; merged into
                    ``AgentContext.shared_state`` by the composition layer.
    *error*       — human-readable error message when ``success=False``.
    *duration_ms* — wall-clock time the agent's ``execute()`` took.
    *retries*     — number of retry attempts that were made before this result.
    *metadata*    — optional extra info (model used, tokens, source counts …).
    """

    success: bool
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    duration_ms: float = 0.0
    retries: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "duration_ms": round(self.duration_ms, 2),
            "retries": self.retries,
            "metadata": self.metadata,
        }

    @classmethod
    def ok(cls, output: dict[str, Any], **kwargs) -> AgentResult:
        """Convenience constructor for a successful result."""
        return cls(success=True, output=output, **kwargs)

    @classmethod
    def fail(cls, error: str, **kwargs) -> AgentResult:
        """Convenience constructor for a failed result."""
        return cls(success=False, error=error, **kwargs)
