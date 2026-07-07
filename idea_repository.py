"""Backward-compatibility shim — IdeaRepository has moved to the BuildNext plugin.

Import from ghostflow.plugins.buildnext.storage.repositories.idea_repository instead.
"""

from ghostflow.plugins.buildnext.storage.repositories.idea_repository import (
    IdeaRepository,  # noqa: F401
)
