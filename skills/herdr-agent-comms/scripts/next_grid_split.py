#!/usr/bin/env python3
"""Pick the next pane to split for an equal-width column grid layout.

All panes in the tab (root + every sub-agent) are kept as equal-width
columns side by side, left to right. Adding the Nth pane means:
  1. Split the rightmost (last) column `right` so the new pane lands as
     the new rightmost column, sized to the target equal share.
  2. Resize every pre-existing column down to that same equal share (they
     were each 1/(N-1) wide before the split; they need to become 1/N).

This intentionally replaces the older "largest pane by area, direction from
aspect ratio" heuristic: that heuristic optimized for a balanced 2D grid,
not for uniform column width. Equal-width columns are a stronger, simpler
constraint that a single split's ratio cannot satisfy on its own once more
than one column already exists — the already-placed columns must also be
resized, which is why this script emits a resize plan, not just a target
pane and direction.

Reads `herdr pane layout` for the root/tab area (or a supplied JSON dump).

Usage:
    python3 next_grid_split.py [--root-pane PANE_ID] [--layout-json PATH|-]

Output: one line per action, so a caller can feed each directly to `herdr`:

    split <rightmost_pane_id> right --ratio <new_pane_share>
    resize <pane_id> <target_width_fraction>
    resize <pane_id> <target_width_fraction>
    ...

`<new_pane_share>` and `<target_width_fraction>` are both `1 / N` where N is
the column count *after* the split (existing columns + the new one). The
exact `herdr pane split --ratio` / `herdr pane resize --amount` semantics
(fraction of remaining space vs. absolute tab fraction vs. cells) are not
verified against a live `herdr` server by this script or its tests — the
caller is responsible for confirming those semantics against the installed
`herdr` version before trusting the resize step blindly (see SKILL.md
Phase 2a and the "Equal-width columns" note there).

Exit codes:
    0 success
    1 usage / environment / parse error
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys


def load_layout(root_pane: str | None, layout_json: str | None) -> dict:
    if layout_json == "-":
        return json.load(sys.stdin)
    if layout_json:
        with open(layout_json, encoding="utf-8") as f:
            return json.load(f)

    if not shutil.which("herdr"):
        raise SystemExit("herdr not on PATH")

    cmd = ["herdr", "pane", "layout"]
    if root_pane:
        cmd.extend(["--pane", root_pane])
    else:
        cmd.append("--current")
    cp = subprocess.run(cmd, text=True, capture_output=True, check=False)
    if cp.returncode != 0:
        raise SystemExit(cp.stderr.strip() or cp.stdout.strip() or "herdr pane layout failed")
    return json.loads(cp.stdout)


def panes_from_layout(data: dict) -> list[dict]:
    layout = data.get("result", data).get("layout", data.get("result", data))
    panes = layout.get("panes") if isinstance(layout, dict) else None
    if not isinstance(panes, list) or not panes:
        raise SystemExit("layout JSON has no panes")
    return panes


def _pane_ids_left_to_right(panes: list[dict]) -> list[str]:
    """Order panes by rect.x so 'rightmost column' is well-defined.

    Panes without a usable rect are dropped rather than guessed at — a
    missing x/width is a layout-shape error the caller should see, not
    something to silently default to 0.
    """
    ordered: list[tuple[float, str]] = []
    for pane in panes:
        pane_id = pane.get("pane_id")
        rect = pane.get("rect") or {}
        try:
            x = float(rect.get("x", 0))
            width = float(rect.get("width", 0))
        except (TypeError, ValueError):
            continue
        if not pane_id or width <= 0:
            continue
        ordered.append((x, pane_id))
    if not ordered:
        raise SystemExit("no usable pane rects in layout")
    ordered.sort(key=lambda t: t[0])
    return [pid for _, pid in ordered]


def plan_equal_width_split(panes: list[dict], root_pane: str | None) -> tuple[list[str], float]:
    """Return (ordered_pane_ids_left_to_right, new_column_count) for the
    caller to build the split + resize plan from. `root_pane` is accepted
    for interface symmetry with the previous largest-pane heuristic and to
    let a caller sanity-check root is present; it does not change the
    equal-width plan (every column — root included — always converges to
    the same share).
    """
    ordered = _pane_ids_left_to_right(panes)
    if root_pane and root_pane not in ordered:
        # Not fatal — layout JSON may come from a fixture/test — but the
        # caller should know root isn't part of what it's about to resize.
        print(f"Warning: root pane {root_pane!r} not found in layout", file=sys.stderr)
    new_count = len(ordered) + 1
    return ordered, new_count


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--root-pane",
        help="root/orchestrator pane id; checked for presence, not otherwise special",
    )
    ap.add_argument(
        "--layout-json",
        help="layout JSON path, or '-' for stdin (skips herdr pane layout)",
    )
    args = ap.parse_args()

    try:
        data = load_layout(args.root_pane, args.layout_json)
        ordered, new_count = plan_equal_width_split(panes_from_layout(data), args.root_pane)
    except (OSError, json.JSONDecodeError, SystemExit) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    share = 1.0 / new_count
    rightmost = ordered[-1]
    print(f"split {rightmost} right --ratio {share:.6f}")
    for pane_id in ordered:
        print(f"resize {pane_id} {share:.6f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
