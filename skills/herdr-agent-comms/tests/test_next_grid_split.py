#!/usr/bin/env python3
"""Fixture tests for next_grid_split.py's pane-selection algorithm.

Run directly (stdlib unittest only, no live herdr needed):
    python3 -m unittest discover -s skills/herdr-agent-comms/tests -p 'test_*.py'
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from next_grid_split import choose_target  # noqa: E402


def panes(*rects):
    return [
        {"pane_id": pid, "rect": {"width": w, "height": h}}
        for pid, w, h in rects
    ]


class ChooseTargetTests(unittest.TestCase):
    def test_first_split_of_single_pane_always_down(self):
        # Regression guard for the documented "vertical panel first" default:
        # a lone, wide root pane must still split down, not right, even
        # though a naive aspect check on 200x50 would pick right.
        layout = panes(("root", 200, 50))
        target, direction = choose_target(layout, "root")
        self.assertEqual(target, "root")
        self.assertEqual(direction, "down")

    def test_first_split_of_single_pane_down_even_when_tall(self):
        layout = panes(("root", 40, 200))
        target, direction = choose_target(layout, "root")
        self.assertEqual(target, "root")
        self.assertEqual(direction, "down")

    def test_later_split_picks_largest_pane(self):
        layout = panes(("root", 100, 25), ("sub1", 200, 25))
        target, _direction = choose_target(layout, "root")
        self.assertEqual(target, "sub1")

    def test_later_split_ties_prefer_root(self):
        layout = panes(("root", 200, 25), ("sub1", 200, 25))
        target, _direction = choose_target(layout, "root")
        self.assertEqual(target, "root")

    def test_later_split_direction_follows_target_aspect_wide(self):
        layout = panes(("root", 200, 25), ("sub1", 200, 25))
        _target, direction = choose_target(layout, "root")
        self.assertEqual(direction, "right")

    def test_later_split_targets_largest_even_if_another_pane_is_taller(self):
        # "a" is the largest pane by area (200x25=5000 > 40x50=2000) and is
        # wide, so it's both the target and gets `right`.
        layout = panes(("a", 200, 25), ("b", 40, 50))
        target, direction = choose_target(layout, "a")
        self.assertEqual(target, "a")
        self.assertEqual(direction, "right")

    def test_later_split_direction_down_for_tall_target(self):
        layout = panes(("root", 40, 200), ("sub1", 10, 10))
        target, direction = choose_target(layout, "root")
        self.assertEqual(target, "root")
        self.assertEqual(direction, "down")

    def test_missing_root_pane_falls_back_to_largest(self):
        layout = panes(("a", 50, 50), ("b", 100, 100))
        target, _direction = choose_target(layout, None)
        self.assertEqual(target, "b")

    def test_no_usable_rects_raises(self):
        layout = [{"pane_id": "x", "rect": {"width": 0, "height": 0}}]
        with self.assertRaises(SystemExit):
            choose_target(layout, "x")

    def test_three_agent_spawn_sequence_produces_balanced_grid(self):
        """End-to-end simulation: spawn 3 sub-agents from one root pane and
        confirm no pane degenerates into a narrow sliver (regression guard
        for the "wide roots only create narrow columns" bug).
        """
        state = {"root": {"w": 200.0, "h": 50.0}}

        def split(pane_id, direction):
            w, h = state[pane_id]["w"], state[pane_id]["h"]
            new_id = f"p{len(state) + 1}"
            if direction == "down":
                state[pane_id] = {"w": w, "h": h / 2}
                state[new_id] = {"w": w, "h": h / 2}
            else:
                state[pane_id] = {"w": w / 2, "h": h}
                state[new_id] = {"w": w / 2, "h": h}
            return new_id

        for _ in range(3):
            layout = panes(*[(pid, v["w"], v["h"]) for pid, v in state.items()])
            target, direction = choose_target(layout, "root")
            split(target, direction)

        self.assertEqual(len(state), 4)  # root + 3 sub-agents
        areas = [v["w"] * v["h"] for v in state.values()]
        # Balanced grid: no pane should be a sliver relative to an even split.
        even_share = (200.0 * 50.0) / 4
        for area in areas:
            self.assertGreater(area, even_share * 0.4)
            self.assertLess(area, even_share * 2.5)


if __name__ == "__main__":
    unittest.main()
