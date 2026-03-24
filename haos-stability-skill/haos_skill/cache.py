from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Protocol

from .safety import payload_hash


class CacheProtocol(Protocol):
    def get(self, namespace: str, payload: Mapping[str, Any]) -> Optional[dict[str, Any]]:
        ...

    def set(self, namespace: str, payload: Mapping[str, Any], value: Mapping[str, Any]) -> None:
        ...


@dataclass
class NullCache:
    def get(self, namespace: str, payload: Mapping[str, Any]) -> Optional[dict[str, Any]]:
        return None

    def set(self, namespace: str, payload: Mapping[str, Any], value: Mapping[str, Any]) -> None:
        return None


@dataclass
class DeterministicHashCache:
    max_entries: int = 256
    _store: "OrderedDict[str, dict[str, Any]]" = field(default_factory=OrderedDict)

    def make_key(self, namespace: str, payload: Mapping[str, Any]) -> str:
        return "%s:%s" % (namespace, payload_hash(payload))

    def get(self, namespace: str, payload: Mapping[str, Any]) -> Optional[dict[str, Any]]:
        key = self.make_key(namespace, payload)
        cached = self._store.get(key)
        if cached is None:
            return None
        self._store.move_to_end(key)
        return deepcopy(cached)

    def set(self, namespace: str, payload: Mapping[str, Any], value: Mapping[str, Any]) -> None:
        key = self.make_key(namespace, payload)
        self._store[key] = deepcopy(dict(value))
        self._store.move_to_end(key)
        while len(self._store) > self.max_entries:
            self._store.popitem(last=False)
