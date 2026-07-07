"""Backward-compatibility shim — MemoryRepository has moved to the BuildNext plugin.

Import from ghostflow.plugins.buildnext.storage.repositories.memory_repository instead.
"""

from ghostflow.plugins.buildnext.storage.repositories.memory_repository import (
    MemoryRepository,  # noqa: F401
)
