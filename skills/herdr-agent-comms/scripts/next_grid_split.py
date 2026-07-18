#!/usr/bin/env python3
"""Pick the next pane to split for a balanced grid layout.

Reads `herdr pane layout` for the root/tab area and chooses:
  - the largest pane by area (ties prefer the root pane when provided)
  - direction `down` when that pane is taller than or as tall as it is wide
    (vertical panel / stack first), else `right`

This keeps the root agent and every sub-agent in one tiled grid instead of
stacking every new split off a single pane.

Usage:
    python3 next_grid_split.py [--root-pane PANE_ID] [--layout-json PATH|-]

Prints: <pane_id> <right|down>

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


def choose_target(panes: list[dict], root_pane: str | None) -> tuple[str, str]:
    best: dict | None = None
    best_area = -1
    for pane in panes:
        pane_id = pane.get("pane_id")
        rect = pane.get("rect") or {}
        try:
            width = float(rect.get("width", 0))
            height = float(rect.get("height", 0))
        except (TypeError, ValueError):
            continue
        if not pane_id or width <= 0 or height <= 0:
            continue
        area = width * height
        # Prefer root on area ties so the orchestrator stays in the grid plan.
        better = area > best_area or (
            area == best_area and root_pane and pane_id == root_pane
        )
        if better or best is None:
            best = {"pane_id": pane_id, "width": width, "height": height}
            best_area = area

    if best is None:
        raise SystemExit("no usable pane rects in layout")

    # Prefer vertical panels first: stack top/bottom unless the cell is clearly wider.
    direction = "down" if best["height"] >= best["width"] else "right"
    return best["pane_id"], direction


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--root-pane",
        help="root/orchestrator pane id; preferred on area ties",
    )
    ap.add_argument(
        "--layout-json",
        help="layout JSON path, or '-' for stdin (skips herdr pane layout)",
    )
    args = ap.parse_args()

    try:
        data = load_layout(args.root_pane, args.layout_json)
        target, direction = choose_target(panes_from_layout(data), args.root_pane)
    except (OSError, json.JSONDecodeError, SystemExit) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print(f"{target} {direction}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
