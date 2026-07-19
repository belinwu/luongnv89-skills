#!/usr/bin/env python3
"""Fixture tests for next_grid_split.py's equal-width column planning.

Run directly (stdlib unittest only, no live herdr needed):
    python3 -m unittest discover -s skills/herdr-agent-comms/tests -p 'test_*.py'

These cover the pure arithmetic that decides the split ratio and each
equalizer resize op. The exact `herdr pane split --ratio` / `herdr pane
resize --amount` semantics they encode were verified LIVE against herdr
0.7.4 (documented in SKILL.md "Equal-width columns — verified semantics"):
`--ratio` = the existing/left child's fraction of the split pane; `--amount`
= a cell delta as a fraction of the tab area width, growing the neighbor on
`--direction`. `test_equalizer_sweep_converges_on_redistribution_model`
simulates the observed proportional redistribution and confirms the
outermost-first grow sweep is a contraction (converges to equal width).
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from next_grid_split import (  # noqa: E402
    area_width_from_layout,
    boundary_resize_op,
    equal_targets,
    panes_from_layout,
    plan_next_split,
    require_root_membership,
    split_ratio,
    validate_single_row,
)


def panes(*rects):
    return [
        {"pane_id": pid, "rect": {"x": x, "width": w}}
        for pid, x, w in rects
    ]


def full_rect_layout(area, *rects):
    """Layout with full x/y/width/height rects, for validate_single_row.

    `area` is (x, y, width, height); each rect is (pid, x, y, width, height).
    """
    ax, ay, aw, ah = area
    return {
        "result": {
            "layout": {
                "area": {"x": ax, "y": ay, "width": aw, "height": ah},
                "panes": [
                    {"pane_id": pid, "rect": {"x": x, "y": y, "width": w, "height": h}}
                    for pid, x, y, w, h in rects
                ],
            }
        }
    }


class PlanNextSplitTests(unittest.TestCase):
    def test_single_pane_plans_two_columns(self):
        rightmost, new_count = plan_next_split(panes(("root", 0, 200)), "root")
        self.assertEqual(rightmost, "root")
        self.assertEqual(new_count, 2)

    def test_orders_panes_left_to_right_and_splits_rightmost(self):
        rightmost, new_count = plan_next_split(
            panes(("sub1", 100, 100), ("root", 0, 100)), "root"
        )
        self.assertEqual(rightmost, "sub1")
        self.assertEqual(new_count, 3)

    def test_three_existing_columns_plans_fourth(self):
        rightmost, new_count = plan_next_split(
            panes(("root", 0, 66), ("sub1", 66, 67), ("sub2", 133, 67)), "root"
        )
        self.assertEqual(rightmost, "sub2")
        self.assertEqual(new_count, 4)

    def test_no_root_requested_still_plans_from_layout(self):
        # root_pane is None => "no specific root requested", plan normally.
        rightmost, new_count = plan_next_split(panes(("a", 0, 50), ("b", 50, 50)), None)
        self.assertEqual(rightmost, "b")
        self.assertEqual(new_count, 3)

    def test_requested_root_absent_from_layout_is_hard_error(self):
        # P4 round 6: a named root that isn't in the layout means we'd be
        # splitting the WRONG tab — must raise before any mutation, not warn.
        with self.assertRaises(SystemExit):
            plan_next_split(panes(("a", 0, 50), ("b", 50, 50)), "missing-root")

    def test_requested_root_present_plans_normally(self):
        rightmost, new_count = plan_next_split(panes(("a", 0, 50), ("b", 50, 50)), "a")
        self.assertEqual(rightmost, "b")
        self.assertEqual(new_count, 3)

    def test_no_usable_rects_raises(self):
        with self.assertRaises(SystemExit):
            plan_next_split([{"pane_id": "x", "rect": {"x": 0, "width": 0}}], "x")

    def test_panes_missing_rect_fields_are_dropped(self):
        layout = [
            {"pane_id": "root", "rect": {"x": 0, "width": 100}},
            {"pane_id": "ghost"},
        ]
        rightmost, new_count = plan_next_split(layout, "root")
        self.assertEqual(rightmost, "root")
        self.assertEqual(new_count, 2)


class MalformedLayoutJsonTests(unittest.TestCase):
    """Round 14 note: malformed-but-valid JSON must yield a clean SystemExit
    validation error, NOT an uncaught AttributeError traceback."""

    def test_top_level_null_is_clean_error(self):
        # json.load of "null" is None; .get() on it would crash.
        with self.assertRaises(SystemExit):
            panes_from_layout(None)

    def test_top_level_list_is_clean_error(self):
        with self.assertRaises(SystemExit):
            panes_from_layout([1, 2, 3])

    def test_panes_with_null_element_is_clean_error(self):
        # `panes: [null]` — the null element would crash every pane.get(...).
        with self.assertRaises(SystemExit):
            panes_from_layout({"layout": {"panes": [None]}})

    def test_panes_with_non_object_element_is_clean_error(self):
        with self.assertRaises(SystemExit):
            panes_from_layout({"layout": {"panes": ["not-a-pane"]}})

    def test_null_element_via_validate_single_row_is_clean_error(self):
        with self.assertRaises(SystemExit):
            validate_single_row({"layout": {"area": {"x": 0, "y": 0, "width": 100, "height": 10},
                                            "panes": [None]}})

    def test_null_element_via_plan_next_split_is_clean_error(self):
        with self.assertRaises(SystemExit):
            plan_next_split([None], "root")


class RequireRootMembershipTests(unittest.TestCase):
    def test_none_root_is_allowed(self):
        require_root_membership(["a", "b"], None)  # must not raise

    def test_present_root_is_allowed(self):
        require_root_membership(["a", "b"], "a")

    def test_absent_root_raises(self):
        with self.assertRaises(SystemExit):
            require_root_membership(["a", "b"], "missing")

    def test_absent_root_in_empty_layout_raises(self):
        with self.assertRaises(SystemExit):
            require_root_membership([], "root")


class SplitRatioTests(unittest.TestCase):
    """`--ratio` = 1/N (the existing/left child's fraction). Verified live
    against herdr 0.7.4: from two equal 105/105 columns, splitting the
    rightmost with ratio 1/3 gives a new pane of 70 (= 210/3, the equal
    target). The earlier (N-1)/N value was BACKWARDS — it made the new pane
    the *small* child (35, not 70)."""

    def test_second_column_is_half(self):
        self.assertEqual(split_ratio(2), 0.5)

    def test_third_column_is_one_third(self):
        self.assertAlmostEqual(split_ratio(3), 1.0 / 3.0, places=9)

    def test_fourth_column_is_one_quarter(self):
        self.assertEqual(split_ratio(4), 0.25)

    def test_ratio_is_reciprocal_of_new_count(self):
        for n in range(2, 12):
            self.assertAlmostEqual(split_ratio(n), 1.0 / n, places=9)

    def test_new_pane_lands_on_equal_target(self):
        """The point of the ratio: splitting the rightmost of N-1 equal
        columns (each 1/(N-1) of the tab) at ratio 1/N makes the new pane
        exactly 1/N of the tab."""
        area = 210.0
        for n in range(2, 8):
            existing = n - 1
            rightmost_col_width = area / existing  # existing columns are equal
            r = split_ratio(n)
            new_pane_width = (1.0 - r) * rightmost_col_width
            self.assertAlmostEqual(new_pane_width, area / n, places=6)

    def test_below_two_raises(self):
        with self.assertRaises(SystemExit):
            split_ratio(1)


class EqualTargetsTests(unittest.TestCase):
    def test_even_division(self):
        self.assertEqual(equal_targets(5, 210), [42, 42, 42, 42, 42])

    def test_remainder_goes_to_leftmost_columns(self):
        # 210 / 4 = 52.5 -> two columns get 53, two get 52; sum stays 210.
        self.assertEqual(equal_targets(4, 210), [53, 53, 52, 52])
        self.assertEqual(sum(equal_targets(4, 210)), 210)

    def test_single_column(self):
        self.assertEqual(equal_targets(1, 210), [210])

    def test_zero_columns_raises(self):
        with self.assertRaises(SystemExit):
            equal_targets(0, 210)


class BoundaryResizeOpTests(unittest.TestCase):
    ids = ["a", "b", "c"]

    def test_boundary_must_move_right_grows_left_column(self):
        # widths 40/80/90 (area 210), targets 70/70/70. Boundary 0 cum=40,
        # target cum=70 -> move right by 30 -> grow column a on its right.
        op = boundary_resize_op(self.ids, [40, 80, 90], [70, 70, 70], 210, 0)
        self.assertEqual(op, ("a", "right", 30 / 210))

    def test_boundary_must_move_left_grows_right_column(self):
        # widths 105/53/52, targets 70/70/70. Boundary 0 cum=105, target=70
        # -> move left by 35 -> grow the RIGHT column b on its left edge.
        op = boundary_resize_op(self.ids, [105, 53, 52], [70, 70, 70], 210, 0)
        self.assertEqual(op, ("b", "left", 35 / 210))

    def test_on_target_returns_none(self):
        op = boundary_resize_op(self.ids, [70, 70, 70], [70, 70, 70], 210, 0)
        self.assertIsNone(op)

    def test_sub_cell_delta_returns_none(self):
        # cum 70.4 vs target 70 -> 0.4 cell, nothing herdr can act on.
        op = boundary_resize_op(self.ids, [70.4, 70, 69.6], [70, 70, 70], 210, 0)
        self.assertIsNone(op)


class AreaWidthTests(unittest.TestCase):
    def test_reads_explicit_area(self):
        data = {"layout": {"area": {"width": 210}, "panes": panes(("a", 0, 210))}}
        self.assertEqual(area_width_from_layout(data), 210)

    def test_falls_back_to_summed_widths(self):
        data = {"layout": {"panes": panes(("a", 0, 100), ("b", 100, 110))}}
        self.assertEqual(area_width_from_layout(data), 210)


class ValidateSingleRowTests(unittest.TestCase):
    """Reject 2D / stacked layouts before any split or equalize (P3 round 5).
    Area = (x, y, w, h); panes carry full x/y/w/h rects."""

    AREA = (0, 0, 210, 55)

    def test_valid_single_row_passes(self):
        layout = full_rect_layout(
            self.AREA,
            ("a", 0, 0, 105, 55),
            ("b", 105, 0, 105, 55),
        )
        validate_single_row(layout)  # must not raise

    def test_valid_three_columns_passes(self):
        layout = full_rect_layout(
            self.AREA,
            ("a", 0, 0, 70, 55),
            ("b", 70, 0, 70, 55),
            ("c", 140, 0, 70, 55),
        )
        validate_single_row(layout)

    def test_stacked_panes_sharing_x_are_rejected(self):
        # b and c share x=105 but are stacked vertically (half height each) —
        # the column model would double-count them. Must reject.
        layout = full_rect_layout(
            self.AREA,
            ("a", 0, 0, 105, 55),
            ("b", 105, 0, 105, 27),
            ("c", 105, 27, 105, 28),
        )
        with self.assertRaises(SystemExit):
            validate_single_row(layout)

    def test_partial_height_pane_is_rejected(self):
        layout = full_rect_layout(
            self.AREA,
            ("a", 0, 0, 105, 55),
            ("b", 105, 0, 105, 30),  # not full height
        )
        with self.assertRaises(SystemExit):
            validate_single_row(layout)

    def test_top_offset_pane_is_rejected(self):
        layout = full_rect_layout(
            self.AREA,
            ("a", 0, 0, 105, 55),
            ("b", 105, 5, 105, 50),  # not top-aligned with area
        )
        with self.assertRaises(SystemExit):
            validate_single_row(layout)

    def test_gap_between_columns_is_rejected(self):
        layout = full_rect_layout(
            self.AREA,
            ("a", 0, 0, 100, 55),
            ("b", 110, 0, 100, 55),  # gap from 100..110
        )
        with self.assertRaises(SystemExit):
            validate_single_row(layout)

    def test_overlapping_columns_are_rejected(self):
        layout = full_rect_layout(
            self.AREA,
            ("a", 0, 0, 110, 55),
            ("b", 100, 0, 110, 55),  # overlaps a from 100..110
        )
        with self.assertRaises(SystemExit):
            validate_single_row(layout)

    def test_columns_not_filling_width_are_rejected(self):
        layout = full_rect_layout(
            self.AREA,
            ("a", 0, 0, 70, 55),
            ("b", 70, 0, 70, 55),  # spans to 140, area ends at 210
        )
        with self.assertRaises(SystemExit):
            validate_single_row(layout)

    def test_missing_area_rect_is_rejected(self):
        layout = {"result": {"layout": {"panes": panes(("a", 0, 210))}}}
        with self.assertRaises(SystemExit):
            validate_single_row(layout)

    def test_pane_missing_yheight_is_rejected(self):
        # A pane rect with only x/width (the old shape) can't be validated as
        # a full-height column — must reject rather than assume.
        layout = {
            "result": {
                "layout": {
                    "area": {"x": 0, "y": 0, "width": 210, "height": 55},
                    "panes": [{"pane_id": "a", "rect": {"x": 0, "width": 210}}],
                }
            }
        }
        with self.assertRaises(SystemExit):
            validate_single_row(layout)


class EqualizerConvergenceTests(unittest.TestCase):
    """Simulate the live herdr redistribution behaviour and confirm the
    outermost-first, always-grow boundary sweep is a contraction toward
    equal width. The model mirrors what was observed live: a resize moves
    one boundary by the requested delta and redistributes the freed/absorbed
    cells *proportionally* among the panes on the other side of that
    boundary.
    """

    AREA = 210

    def _resize(self, widths, pane_index, direction, amount):
        """Apply one resize to a copy of `widths`, returning the new list.

        Moves the boundary between `pane_index` and its neighbor on
        `direction`, redistributing `delta` cells proportionally across the
        panes on the far side of that boundary.
        """
        w = list(widths)
        delta = amount * self.AREA
        if direction == "right":
            # grow pane_index rightward: boundary between pane_index and
            # pane_index+1 moves right; cells taken from all panes to the right.
            w[pane_index] += delta
            right = list(range(pane_index + 1, len(w)))
            total = sum(w[i] for i in right)
            for i in right:
                w[i] -= delta * (w[i] / total)
        else:  # left: grow pane_index leftward, boundary between it and
            # pane_index-1 moves left; cells taken from panes to the left.
            w[pane_index] += delta
            left = list(range(0, pane_index))
            total = sum(w[i] for i in left)
            for i in left:
                w[i] -= delta * (w[i] / total)
        return w

    def _sweep_once(self, widths):
        ids = [f"c{i}" for i in range(len(widths))]
        targets = equal_targets(len(widths), self.AREA)
        for boundary in range(len(widths) - 1):
            op = boundary_resize_op(ids, widths, targets, self.AREA, boundary)
            if op is None:
                continue
            pane_id, direction, amount = op
            idx = ids.index(pane_id)
            widths = self._resize(widths, idx, direction, amount)
        return widths

    def test_four_column_decay_converges(self):
        # geometric decay a naive split leaves behind: 105/35/18/52-ish.
        widths = [105.0, 35.0, 18.0, 52.0]
        # normalize to area
        scale = self.AREA / sum(widths)
        widths = [w * scale for w in widths]
        start_spread = max(widths) - min(widths)
        for _ in range(12):
            if max(widths) - min(widths) <= 1.5:
                break
            widths = self._sweep_once(widths)
        # This float model converges to ~1 cell; live herdr (integer cells)
        # lands at spread 0 for this case. Either way the sweep is a strong
        # contraction — assert it collapsed to a near-equal fixed point.
        self.assertLess(max(widths) - min(widths), start_spread)
        self.assertLessEqual(max(widths) - min(widths), 1.5)

    def test_already_equal_is_a_fixed_point(self):
        widths = [70.0, 70.0, 70.0]
        out = self._sweep_once(widths)
        for a, b in zip(out, widths):
            self.assertAlmostEqual(a, b, places=6)


if __name__ == "__main__":
    unittest.main()
