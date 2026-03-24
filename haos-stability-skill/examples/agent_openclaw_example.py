from __future__ import annotations

import os

from haos_skill import evaluate_structure


os.environ.setdefault("HAOS_ORACLE_COMMAND", "haos_iip.demo stability --json")


def register_with_agent(agent) -> None:
    agent.register_skill(evaluate_structure)
