#!/usr/bin/env python3
"""Fixture tests for next_grid_split.py's equal-width column planning.

Run directly (stdlib unittest only, no live herdr needed):
    python3 -m unittest discover -s skills/herdr-agent-comms/tests -p 'test_*.py'

Covers the pure-arithmetic core only (ordering panes left to right, and the
1/N share for N columns after a split). The actual `herdr pane split
--ratio` / `herdr pane resize --amount` semantics are NOT exercised here —
there is no live herdr server in this test harness to confirm what those
flags actually do; see the module docstring in next_grid_split.py.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from next_grid_split import plan_equal_width_split  # noqa: E402


def panes(*rects):
    return [
        {"pane_id": pid, "rect": {"x": x, "width": w}}
        for pid, x, w in rects
    ]


class PlanEqualWidthSplitTests(unittest.TestCase):
    def test_single_pane_plans_two_columns(self):
        layout = panes(("root", 0, 200))
        ordered, new_count = plan_equal_width_split(layout, "root")
        self.assertEqual(ordered, ["root"])
        self.assertEqual(new_count, 2)

    def test_orders_panes_left_to_right_by_x(self):
        layout = panes(("sub1", 100, 100), ("root", 0, 100))
        ordered, new_count = plan_equal_width_split(layout, "root")
        self.assertEqual(ordered, ["root", "sub1"])
        self.assertEqual(new_count, 3)

    def test_three_existing_columns_plans_fourth(self):
        layout = panes(("root", 0, 66), ("sub1", 66, 67), ("sub2", 133, 67))
        ordered, new_count = plan_equal_width_split(layout, "root")
        self.assertEqual(ordered, ["root", "sub1", "sub2"])
        self.assertEqual(new_count, 4)

    def test_missing_root_pane_still_plans_from_layout(self):
        layout = panes(("a", 0, 50), ("b", 50, 50))
        ordered, new_count = plan_equal_width_split(layout, None)
        self.assertEqual(ordered, ["a", "b"])
        self.assertEqual(new_count, 3)

    def test_root_pane_not_in_layout_warns_but_still_plans(self):
        layout = panes(("a", 0, 50), ("b", 50, 50))
        ordered, new_count = plan_equal_width_split(layout, "missing-root")
        self.assertEqual(ordered, ["a", "b"])
        self.assertEqual(new_count, 3)

    def test_no_usable_rects_raises(self):
        layout = [{"pane_id": "x", "rect": {"x": 0, "width": 0}}]
        with self.assertRaises(SystemExit):
            plan_equal_width_split(layout, "x")

    def test_panes_missing_rect_fields_are_dropped(self):
        layout = [
            {"pane_id": "root", "rect": {"x": 0, "width": 100}},
            {"pane_id": "ghost"},
        ]
        ordered, new_count = plan_equal_width_split(layout, "root")
        self.assertEqual(ordered, ["root"])
        self.assertEqual(new_count, 2)

    def test_four_agent_spawn_sequence_converges_to_equal_shares(self):
        """End-to-end simulation: spawn 3 sub-agents from one root pane,
        each time re-running the planner and applying the emitted resize
        plan, and confirm every column ends up the same width.
        """
        state = {"root": {"x": 0.0, "w": 200.0}}

        def apply_plan(ordered, new_count):
            share = 200.0 / new_count
            new_id = f"p{len(state) + 1}"
            state[new_id] = {"x": 0.0, "w": share}
            x = 0.0
            for pane_id in ordered + [new_id]:
                state[pane_id]["x"] = x
                state[pane_id]["w"] = share
                x += share

        for _ in range(3):
            layout = panes(*[(pid, v["x"], v["w"]) for pid, v in state.items()])
            ordered, new_count = plan_equal_width_split(layout, "root")
            apply_plan(ordered, new_count)

        self.assertEqual(len(state), 4)  # root + 3 sub-agents
        widths = [v["w"] for v in state.values()]
        expected = 200.0 / 4
        for w in widths:
            self.assertAlmostEqual(w, expected, places=6)


if __name__ == "__main__":
    unittest.main()
