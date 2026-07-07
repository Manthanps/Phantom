from __future__ import annotations

from datetime import UTC, datetime

from watchdog.events import (
    DirCreatedEvent,
    DirDeletedEvent,
    DirMovedEvent,
    FileCreatedEvent,
    FileDeletedEvent,
    FileModifiedEvent,
    FileMovedEvent,
    FileSystemEvent,
)

from ghostflow.models import ActivityEvent, EventSource, EventType

_EVENT_TYPE_MAP: dict[type[FileSystemEvent], EventType] = {
    FileCreatedEvent: EventType.FILE_CREATED,
    FileModifiedEvent: EventType.FILE_MODIFIED,
    FileDeletedEvent: EventType.FILE_DELETED,
    FileMovedEvent: EventType.FILE_MOVED,
    DirCreatedEvent: EventType.FOLDER_CREATED,
    DirDeletedEvent: EventType.FOLDER_DELETED,
    DirMovedEvent: EventType.FOLDER_MOVED,
}

_MOVE_TYPES: frozenset[type[FileSystemEvent]] = frozenset({FileMovedEvent, DirMovedEvent})


def normalize_event(raw: FileSystemEvent) -> ActivityEvent | None:
    event_type = _EVENT_TYPE_MAP.get(type(raw))
    if event_type is None:
        return None

    is_move = type(raw) in _MOVE_TYPES
    # For moves: path = new location, old_path = previous location
    path = str(raw.dest_path) if is_move else str(raw.src_path)
    old_path = str(raw.src_path) if is_move else None

    return ActivityEvent(
        event_type=event_type,
        source=EventSource.FILE_SYSTEM,
        path=path,
        old_path=old_path,
        timestamp=datetime.now(tz=UTC),
        metadata={"is_directory": raw.is_directory},
    )
