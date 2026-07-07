from __future__ import annotations

import time
from collections.abc import Callable

from rich.console import Console
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from ghostflow.config import WATCH_DIR
from ghostflow.models import ActivityEvent
from ghostflow.observation.base_observer import BaseObserver
from ghostflow.observation.event_normalizer import normalize_event

console = Console()

_COLOR: dict[str, str] = {
    "file_created": "green",
    "file_modified": "yellow",
    "file_deleted": "red",
    "file_moved": "blue",
    "folder_created": "cyan",
    "folder_deleted": "red",
    "folder_moved": "blue",
}


class _EventHandler(FileSystemEventHandler):
    DEBOUNCE_SECONDS: float = 0.5

    def __init__(self, callback: Callable[[ActivityEvent], None]) -> None:
        super().__init__()
        self._callback = callback
        # key: (event_class_name, src_path) → last emit time
        self._last_seen: dict[tuple[str, str], float] = {}

    def on_any_event(self, raw: FileSystemEvent) -> None:
        key = (type(raw).__name__, raw.src_path)
        now = time.monotonic()

        if now - self._last_seen.get(key, 0.0) < self.DEBOUNCE_SECONDS:
            return
        self._last_seen[key] = now

        # Prune stale entries so the dict doesn't grow unbounded
        if len(self._last_seen) > 500:
            cutoff = now - 5.0
            self._last_seen = {k: v for k, v in self._last_seen.items() if v > cutoff}

        event = normalize_event(raw)
        if event:
            self._callback(event)


class FileObserver(BaseObserver):
    def __init__(self, watch_dir: str | None = None) -> None:
        self._watch_dir = str(watch_dir or WATCH_DIR)
        self._observer: Observer = Observer()
        self._running: bool = False

    def start(self) -> None:
        handler = _EventHandler(self._emit)
        self._observer.schedule(handler, self._watch_dir, recursive=True)
        self._observer.start()
        self._running = True
        console.print(
            f"[bold green]Observer started[/bold green] → watching [cyan]{self._watch_dir}[/cyan]"
        )

    def stop(self) -> None:
        self._observer.stop()
        self._observer.join()
        self._running = False
        console.print("[bold yellow]Observer stopped[/bold yellow]")

    def is_running(self) -> bool:
        return self._running and self._observer.is_alive()

    def _emit(self, event: ActivityEvent) -> None:
        color = _COLOR.get(event.event_type.value, "white")
        move_line = f"\n  [dim]← {event.old_path}[/dim]" if event.old_path else ""
        console.print(
            f"[{color}]{event.event_type.value:<18}[/{color}]"
            f"  [dim]{event.timestamp.strftime('%H:%M:%S.%f')[:-3]}[/dim]"
            f"  {event.path}"
            f"{move_line}"
        )
