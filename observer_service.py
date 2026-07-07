from __future__ import annotations

from typing import Any

from ghostflow.observation.base_observer import BaseObserver
from ghostflow.observation.file_observer import FileObserver


class ObserverService:
    def __init__(self, observers: list[BaseObserver] | None = None) -> None:
        self._observers: list[BaseObserver] = (
            observers if observers is not None else [FileObserver()]
        )

    def start_all(self) -> None:
        for obs in self._observers:
            obs.start()

    def stop_all(self) -> None:
        for obs in self._observers:
            if obs.is_running():
                obs.stop()

    def status(self) -> dict[str, Any]:
        total = len(self._observers)
        running = sum(1 for obs in self._observers if obs.is_running())
        return {
            "observers": total,
            "running": running,
            "healthy": running == total,
        }
