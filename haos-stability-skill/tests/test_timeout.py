from __future__ import annotations

import subprocess
import unittest
from unittest.mock import patch

from haos_skill.adapter import run_stability_oracle
from haos_skill.safety import SkillTimeoutError


SAMPLE_STATE = {"nodes": [{"id": "a"}], "edges": []}


class TimeoutTests(unittest.TestCase):
    def test_adapter_raises_controlled_timeout(self) -> None:
        with patch(
            "haos_skill.adapter.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd=["haos_iip.demo"], timeout=0.01),
        ):
            with self.assertRaises(SkillTimeoutError):
                run_stability_oracle(SAMPLE_STATE, timeout=0.01, command=("haos_iip.demo", "stability"))


if __name__ == "__main__":
    unittest.main()
