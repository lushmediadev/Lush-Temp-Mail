from __future__ import annotations

import threading
from typing import Iterable

from .utils import normalize_address


class InboxEventBroker:
    def __init__(self) -> None:
        self._condition = threading.Condition()
        self._global_version = 0
        self._alias_versions: dict[str, int] = {}

    def publish(self, aliases: Iterable[str] | None = None) -> dict[str, object]:
        normalized_aliases = sorted({normalize_address(alias) for alias in (aliases or []) if alias})
        with self._condition:
            self._global_version += 1
            alias_versions: dict[str, int] = {}
            for alias in normalized_aliases:
                next_version = self._alias_versions.get(alias, 0) + 1
                self._alias_versions[alias] = next_version
                alias_versions[alias] = next_version
            self._condition.notify_all()
            return {
                "global_version": self._global_version,
                "alias_versions": alias_versions,
            }

    def get_global_version(self) -> int:
        with self._condition:
            return self._global_version

    def get_alias_version(self, alias: str) -> int:
        normalized_alias = normalize_address(alias)
        with self._condition:
            return self._alias_versions.get(normalized_alias, 0)

    def wait_for_global(self, last_version: int, timeout: float) -> int:
        with self._condition:
            if self._global_version != last_version:
                return self._global_version
            self._condition.wait(timeout)
            return self._global_version

    def wait_for_alias(self, alias: str, last_version: int, timeout: float) -> int:
        normalized_alias = normalize_address(alias)
        with self._condition:
            current_version = self._alias_versions.get(normalized_alias, 0)
            if current_version != last_version:
                return current_version
            self._condition.wait(timeout)
            return self._alias_versions.get(normalized_alias, 0)


inbox_events = InboxEventBroker()
