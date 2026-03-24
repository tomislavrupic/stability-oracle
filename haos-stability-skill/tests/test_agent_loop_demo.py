from __future__ import annotations

import unittest

from examples.agent_loop_demo import run_demo


class AgentLoopDemoTests(unittest.TestCase):
    def test_agent_loop_demo_selects_deterministic_stabilizing_trajectory(self) -> None:
        summary = run_demo()

        selected_names = [step["selected"]["action_name"] for step in summary["steps"]]
        self.assertEqual(
            selected_names,
            ["restore_sink", "extend_to_archive", "add_redundant_bridge"],
        )

        classifications = [step["selected"]["classification"] for step in summary["steps"]]
        self.assertEqual(classifications, ["stable", "stable", "stable"])

        final_state = summary["final_state"]
        self.assertEqual(final_state["nodes"], [1, 2, 3, 4, 5])
        self.assertEqual(final_state["edges"], [[1, 2], [2, 3], [3, 4], [4, 5], [2, 4]])


if __name__ == "__main__":
    unittest.main()
