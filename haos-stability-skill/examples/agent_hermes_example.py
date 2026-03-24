from __future__ import annotations

import os

from haos_skill import evaluate_structure, load_schema


os.environ.setdefault("HAOS_ORACLE_COMMAND", "haos_iip.demo stability --json")


def register_with_registry(tool_registry) -> None:
    tool_registry.add(load_schema()["tools"][0], evaluate_structure)
