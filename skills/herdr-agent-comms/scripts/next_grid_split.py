#!/usr/bin/env python3
"""Plan (and optionally drive) an equal-width column grid in a Herdr tab.

All panes in the tab (root + every sub-agent) are kept as equal-width
columns side by side, left to right. This models the *real* Herdr 0.7.4
`pane split` / `pane resize` semantics, verified live against a running
herdr server (see SKILL.md "Equal-width columns — verified semantics"):

  * `herdr pane split <pane> --direction right --ratio R`
        R is the fraction the EXISTING (first/left) child keeps of the
        pane being split; the new pane gets (1 - R). It only resizes the
        pane you split — the other columns are untouched. So a single
        split can NEVER equalize N >= 3 columns on its own.

  * `herdr pane resize --pane P --direction D --amount A`
        A is a DELTA expressed as a fraction of the whole tab area width
        (A * area_width cells), NOT an absolute target width. `--direction`
        moves the edge on side D: for a pane that has a neighbor on side D
        it GROWS toward that neighbor; against a wall it shrinks. The freed
        or absorbed cells redistribute *proportionally* among the panes on
        the other side of the moved boundary. Because that redistribution
        perturbs columns you already placed, a single left-to-right sweep
        does not land equal — but the sweep is a contraction: iterating it
        converges to equal width within ~1 cell in a handful of passes
        (verified: spread 25 -> 13 -> 5 -> 3 -> 1 for a 4-column decay).

So the reliable strategy this script encodes is:

  1. Add column N by splitting the current rightmost column `right` with
     `--ratio 1/N`. `--ratio R` is the fraction the EXISTING (left) child of
     the split column keeps, so the NEW (right) pane gets `1 - R = (N-1)/N`
     of that column — which, since the rightmost column is `1/(N-1)` of the
     tab when the N-1 existing columns are equal, equals `1/N` of the whole
     tab (the equal target). See `split_ratio()` for the derivation.
  2. Run an iterative boundary equalizer: sweep internal boundaries left
     to right, moving each toward its target cumulative position by GROWING
     the neighbor-bearing pane; repeat until the width spread is <= 1 cell
     (or a small iteration cap). Each pass re-reads the live layout. A resize
     command failure or non-convergence is a HARD error (exit 1), never
     suppressed — the caller must not launch workers into an unequal layout.

Usage:
    # plan the split for the next column (default)
    python3 next_grid_split.py [--root-pane PANE_ID] [--layout-json PATH|-]

    # run the live iterative equalizer over the current tab
    python3 next_grid_split.py --equalize [--root-pane PANE_ID]

Default output (one split line a caller feeds to `herdr pane split`):

    split <rightmost_pane_id> right --ratio <1/N>

where N is the column count AFTER the split. Follow it with `--equalize`
(see SKILL.md Phase 2a).

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

# Equal within this many cells is "done" — herdr rounds column widths to
# whole terminal cells, so exact equality is impossible when area_width is
# not divisible by the column count.
EQUAL_TOLERANCE_CELLS = 1
# Safety cap so a pathological layout can't loop forever. The sweep is a
# contraction; real layouts converge in ~5 passes.
MAX_EQUALIZE_PASSES = 12


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


def _unwrap_layout(data: dict) -> dict:
    """Return the inner `layout` object regardless of whether `data` is the
    raw CLI envelope (`{"result": {"layout": {...}}}`), a `{"layout": {...}}`
    fixture, or the layout dict itself."""
    node = data.get("result", data)
    if isinstance(node, dict) and "layout" in node:
        node = node["layout"]
    if not isinstance(node, dict):
        raise SystemExit("layout JSON is not an object")
    return node


def panes_from_layout(data: dict) -> list[dict]:
    layout = _unwrap_layout(data)
    panes = layout.get("panes")
    if not isinstance(panes, list) or not panes:
        raise SystemExit("layout JSON has no panes")
    return panes


def area_width_from_layout(data: dict) -> float:
    layout = _unwrap_layout(data)
    area = layout.get("area") or {}
    try:
        width = float(area.get("width", 0))
    except (TypeError, ValueError):
        width = 0.0
    if width <= 0:
        # Fall back to the summed pane widths so fixtures without an explicit
        # area still work.
        width = sum(_ordered_columns(panes_from_layout(data))[1])
    if width <= 0:
        raise SystemExit("layout JSON has no usable area width")
    return width


def validate_single_row(data: dict, tolerance: int = 1) -> None:
    """Reject layouts this script cannot safely treat as a row of columns.

    The split/equalize model assumes every pane is a full-height column
    tiling the tab left to right. A 2D layout (vertically stacked panes, or a
    partial-height pane) breaks that: panes sharing an `x` would be counted as
    separate columns, inflating the column total and making the "rightmost
    column" split target ambiguous. This validates x/y/width/height BEFORE any
    mutation and raises SystemExit on anything that isn't a single clean row.

    Requires a real `area` rect (the summed-width fallback in
    `area_width_from_layout` is unsafe here — stacked panes double-count).
    """
    layout = _unwrap_layout(data)
    area = layout.get("area")
    if not isinstance(area, dict):
        raise SystemExit(
            "layout has no 'area' rect; cannot validate a single-row column "
            "grid (refusing to split/equalize a layout of unknown shape)"
        )
    try:
        ax = float(area["x"]); ay = float(area["y"])
        aw = float(area["width"]); ah = float(area["height"])
    except (KeyError, TypeError, ValueError) as e:
        raise SystemExit(f"layout 'area' rect missing x/y/width/height: {e}") from e

    panes = panes_from_layout(data)
    rects: list[tuple[float, float, float, float, str]] = []
    for pane in panes:
        pid = pane.get("pane_id")
        rect = pane.get("rect")
        if not isinstance(rect, dict):
            raise SystemExit(f"pane {pid!r} has no rect; cannot validate layout shape")
        try:
            x = float(rect["x"]); y = float(rect["y"])
            w = float(rect["width"]); h = float(rect["height"])
        except (KeyError, TypeError, ValueError) as e:
            raise SystemExit(f"pane {pid!r} rect missing x/y/width/height: {e}") from e
        rects.append((x, y, w, h, str(pid)))

    # Every pane must be a full-height column, top-aligned with the area.
    for x, y, w, h, pid in rects:
        if abs(y - ay) > tolerance or abs(h - ah) > tolerance:
            raise SystemExit(
                f"pane {pid} is not a full-height column (y={y:g} h={h:g} vs "
                f"area y={ay:g} h={ah:g}): this looks like a 2D / stacked "
                f"layout, which this skill does not support. Rearrange to a "
                f"single row of columns (or spawn agents in separate tabs)."
            )

    # Columns must tile left-to-right with no overlaps or gaps.
    rects.sort(key=lambda t: t[0])
    cursor = ax
    for x, _y, w, _h, pid in rects:
        if abs(x - cursor) > tolerance:
            raise SystemExit(
                f"column {pid} starts at x={x:g}, expected {cursor:g} — panes "
                f"overlap or leave a gap; not a clean single row. Refusing to "
                f"split/equalize."
            )
        cursor += w
    if abs(cursor - (ax + aw)) > tolerance:
        raise SystemExit(
            f"columns span to x={cursor:g} but area ends at {ax + aw:g}; the "
            f"row does not fill the tab width. Refusing to split/equalize."
        )


def _ordered_columns(panes: list[dict]) -> tuple[list[str], list[float]]:
    """Order panes by rect.x and return parallel (ids, widths) lists.

    Panes without a usable rect are dropped rather than guessed at — a
    missing x/width is a layout-shape error the caller should see, not
    something to silently default to 0.
    """
    ordered: list[tuple[float, str, float]] = []
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
        ordered.append((x, pane_id, width))
    if not ordered:
        raise SystemExit("no usable pane rects in layout")
    ordered.sort(key=lambda t: t[0])
    return [pid for _, pid, _ in ordered], [w for _, _, w in ordered]


def _pane_ids_left_to_right(panes: list[dict]) -> list[str]:
    return _ordered_columns(panes)[0]


def equal_targets(n: int, area_width: float) -> list[int]:
    """Equal-width integer column targets summing to `area_width`.

    Splits the +/-1 rounding remainder onto the leftmost columns, matching
    how herdr distributes cells that don't divide evenly.
    """
    if n <= 0:
        raise SystemExit("column count must be positive")
    total = int(round(area_width))
    base = total // n
    rem = total - base * n
    return [base + (1 if i < rem else 0) for i in range(n)]


def boundary_resize_op(
    ids: list[str],
    widths: list[float],
    targets: list[int],
    area_width: float,
    boundary: int,
) -> tuple[str, str, float] | None:
    """Compute the single resize op that moves internal `boundary`
    (between column `boundary` and `boundary+1`) toward its target
    cumulative position, always by GROWING the neighbor-bearing pane.

    Returns `(pane_id, direction, amount)` or None if already on target.
    `amount` is a fraction of `area_width` (the herdr `--amount` unit).

    * boundary must move RIGHT  -> grow left column: resize ids[boundary] right
    * boundary must move LEFT   -> grow right column: resize ids[boundary+1] left
    """
    target_cum = sum(targets[: boundary + 1])
    cur_cum = sum(widths[: boundary + 1])
    delta = target_cum - cur_cum  # >0: boundary too far left, must move right
    if abs(delta) < 1:  # sub-cell; nothing herdr can act on
        return None
    amount = abs(delta) / area_width
    if delta > 0:
        return (ids[boundary], "right", amount)
    return (ids[boundary + 1], "left", amount)


def plan_next_split(panes: list[dict], root_pane: str | None) -> tuple[str, int]:
    """Return `(rightmost_pane_id, new_column_count)` for adding a column."""
    ordered = _pane_ids_left_to_right(panes)
    if root_pane and root_pane not in ordered:
        print(f"Warning: root pane {root_pane!r} not found in layout", file=sys.stderr)
    return ordered[-1], len(ordered) + 1


def split_ratio(new_count: int) -> float:
    """`--ratio` for `herdr pane split` when adding column `new_count` (= N).

    In herdr 0.7.4 `--ratio R` is the fraction the EXISTING (left) child of
    the split pane keeps; the NEW (right) pane gets `1 - R` of that pane. We
    split the current rightmost column, which — when the N-1 existing columns
    are already equal — is `1/(N-1)` of the whole tab. To make the new pane
    the equal target `1/N` of the tab, it must take `((1/N)/(1/(N-1))) =
    (N-1)/N` of the split column, so the existing child keeps `R = 1/N`.

    Verified live against herdr 0.7.4: from two equal 105/105 columns,
    splitting the rightmost with `--ratio 0.333` (=1/3) yields a new pane of
    width 70 (= 210/3, the equal target). See SKILL.md / herdr-recipes.md.
    """
    if new_count < 2:
        raise SystemExit("new column count must be >= 2 to split")
    return 1.0 / new_count


def _run_herdr(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["herdr", *args], text=True, capture_output=True, check=False)


def equalize_live(root_pane: str | None) -> int:
    """Drive the iterative boundary equalizer against a live herdr server.

    Re-reads the layout each pass (resizes perturb downstream columns), and
    stops once the width spread is within EQUAL_TOLERANCE_CELLS or the pass
    cap is hit. Returns 0 on convergence, 1 if it never converged.
    """
    if not shutil.which("herdr"):
        raise SystemExit("herdr not on PATH")

    # Reject 2D / stacked layouts BEFORE any resize — mutating a layout the
    # column model misreads would scramble the panes.
    validate_single_row(load_layout(root_pane, None))

    for _ in range(MAX_EQUALIZE_PASSES):
        data = load_layout(root_pane, None)
        ids, widths = _ordered_columns(panes_from_layout(data))
        area = area_width_from_layout(data)
        n = len(ids)
        if n < 2:
            return 0  # single column is trivially "equal"
        targets = equal_targets(n, area)
        spread = max(widths) - min(widths)
        if spread <= EQUAL_TOLERANCE_CELLS:
            return 0
        for boundary in range(n - 1):
            # Re-read after each resize: one resize shifts every column to the
            # right of the moved boundary, so later ops in this pass need the
            # updated widths to aim correctly.
            data = load_layout(root_pane, None)
            ids, widths = _ordered_columns(panes_from_layout(data))
            area = area_width_from_layout(data)
            targets = equal_targets(len(ids), area)
            if boundary >= len(ids) - 1:
                break
            op = boundary_resize_op(ids, widths, targets, area, boundary)
            if op is None:
                continue
            pane_id, direction, amount = op
            cp = _run_herdr(
                "pane", "resize", "--pane", pane_id,
                "--direction", direction, "--amount", f"{amount:.6f}",
            )
            # A failed resize is a HARD error — silently swallowing it (the
            # old `|| true` behaviour) leaves an unequal layout that the
            # caller then launches workers into. Surface the exact command
            # and herdr's message so the caller can act.
            if cp.returncode != 0:
                detail = (cp.stderr.strip() or cp.stdout.strip()
                          or f"exit {cp.returncode}")
                raise SystemExit(
                    f"herdr pane resize failed for {pane_id} "
                    f"(--direction {direction} --amount {amount:.6f}): {detail}. "
                    f"Layout left unequal; inspect with "
                    f"`herdr pane layout --pane {root_pane or '--current'}`."
                )

    # Final check after the cap. Non-convergence is also a hard error — do
    # not report "best-effort" and let the caller proceed onto an unequal grid.
    data = load_layout(root_pane, None)
    _, widths = _ordered_columns(panes_from_layout(data))
    spread = max(widths) - min(widths)
    if spread <= EQUAL_TOLERANCE_CELLS:
        return 0
    raise SystemExit(
        f"columns did not converge to equal width after {MAX_EQUALIZE_PASSES} "
        f"passes (widths {[int(w) for w in widths]}, spread {spread:.0f} cells). "
        f"Do NOT launch workers into this layout; inspect with "
        f"`herdr pane layout --pane {root_pane or '--current'}` and retry, or "
        f"reduce the column count."
    )


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
    ap.add_argument(
        "--equalize",
        action="store_true",
        help="run the live iterative boundary equalizer over the current tab and exit",
    )
    args = ap.parse_args()

    if args.equalize:
        try:
            return equalize_live(args.root_pane)
        except (OSError, json.JSONDecodeError, SystemExit) as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    try:
        data = load_layout(args.root_pane, args.layout_json)
        # Refuse to plan a split into a 2D / stacked layout — the "rightmost
        # column" target is ambiguous there and the caller would split blindly.
        validate_single_row(data)
        rightmost, new_count = plan_next_split(panes_from_layout(data), args.root_pane)
    except (OSError, json.JSONDecodeError, SystemExit) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # `--ratio R` = the existing/left child's fraction of the split column.
    # R = 1/N makes the NEW (right) pane the equal 1/N target (see split_ratio).
    ratio = split_ratio(new_count)
    print(f"split {rightmost} right --ratio {ratio:.6f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
