from __future__ import annotations

import json
import os

from haos_skill import scan_structure


os.environ.setdefault("HAOS_ORACLE_COMMAND", "haos_iip.demo stability --json")


def main() -> None:
    payload = {
        "cases": [
            {
                "case_id": "demo",
                "state_spec": {
                    "plan_id": "demo",
                    "nodes": [
                        {"id": "ingest", "step_type": "input", "checkpoint": True, "risk_weight": 0.1},
                        {"id": "publish", "step_type": "output", "risk_weight": 0.2},
                    ],
                    "edges": [{"source": "ingest", "target": "publish"}],
                },
            }
        ]
    }
    print(json.dumps(scan_structure(payload), indent=2, sort_keys=False))


if __name__ == "__main__":
    main()
