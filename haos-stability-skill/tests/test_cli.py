from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from haos_skill.cli import main


LEGACY_STATE = {
    "plan_id": "legacy",
    "nodes": [{"id": "a"}],
    "edges": [],
}

ENGINE_TRANSITION = {
    "before": {
        "nodes": [1, 2, 3, 4],
        "edges": [[1, 2], [2, 3], [3, 4]],
        "timestamps": {"1": 0.0, "2": 1.0, "3": 2.0, "4": 3.0},
    },
    "after": {
        "nodes": [1, 2, 3, 4],
        "edges": [[1, 2], [3, 4]],
        "timestamps": {"1": 0.0, "2": 1.0, "3": 2.0, "4": 3.0},
    },
}


class CLITests(unittest.TestCase):
    def test_existing_evaluate_smoke_path_still_uses_skill_surface(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "state.json"
            path.write_text(json.dumps(LEGACY_STATE), encoding="utf-8")

            with patch("haos_skill.cli.evaluate_structure", return_value={"classification": "stable"}) as mocked:
                with patch("haos_skill.cli.build_default_engine") as engine_builder:
                    buffer = io.StringIO()
                    with redirect_stdout(buffer):
                        main(["evaluate", str(path)])

        self.assertEqual(json.loads(buffer.getvalue()), {"classification": "stable"})
        mocked.assert_called_once()
        engine_builder.assert_not_called()

    def test_transition_payload_uses_oracle_engine_and_emits_trace(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "transition.json"
            path.write_text(json.dumps(ENGINE_TRANSITION), encoding="utf-8")

            buffer = io.StringIO()
            with redirect_stdout(buffer):
                main(["evaluate", str(path)])

        payload = json.loads(buffer.getvalue())
        self.assertEqual(payload["classification"], "stable")
        self.assertIn("trace", payload)
        self.assertEqual(payload["trace"]["input_node_count"], 4)


if __name__ == "__main__":
    unittest.main()
