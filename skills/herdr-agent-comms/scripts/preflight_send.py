#!/usr/bin/env python3
"""Fail-closed pre-send readiness check for a single Herdr pane.

Run this immediately BEFORE typing a task (or a lone Enter) into a pane. It
answers one question: is this pane safe to deliver to *right now*? A pane that
is `working`, `blocked`, or whose status can't be verified is NOT safe — sending
into it either races a prior task's completion signal or types the payload into
a trust/auth dialog.

This is the single-target twin of `scripts/broadcast.sh` Phase 1b: the exact
same fail-closed enum validation, in one testable place so the two paths can't
drift. The status enum lives in `wait_for_idle.py` (imported here).

Exit codes (chosen so callers can branch on the reason):
    0  sendable   (idle / done / unknown — validly reported)
    2  working    (a prior task is in flight; wait for it to settle first)
    3  blocked    (a dialog is on screen; a human must answer it)
    4  unverifiable (lookup/parse failed OR an off-enum/garbage status value)
    1  usage error (herdr missing, no pane id)

On a non-zero exit a one-line reason is printed to stderr; nothing is printed
to stdout unless the pane is sendable (then the resolved status is echoed).

Usage:
    python3 preflight_send.py <pane_id>
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wait_for_idle import LOOKUP_FAILED, agent_status  # noqa: E402


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: preflight_send.py <pane_id>", file=sys.stderr)
        return 1
    pane_id = argv[0]
    if not shutil.which("herdr"):
        print("Error: herdr not on PATH", file=sys.stderr)
        return 1

    # agent_status() is already fail-closed + enum-validated: a failed lookup,
    # unparseable JSON, or an off-enum value (numeric/garbage) all come back as
    # LOOKUP_FAILED, never as a spuriously "safe" status.
    st = agent_status(pane_id)
    if st == LOOKUP_FAILED:
        print(
            f"Error: cannot verify status of {pane_id} (lookup/parse failed or "
            f"off-enum value) — refusing to send into an unverifiable pane.",
            file=sys.stderr,
        )
        return 4
    if st == "working":
        print(
            f"Error: {pane_id} is already working — wait for it to settle "
            f"before sending, or this send's completion can't be told apart "
            f"from the prior task's.",
            file=sys.stderr,
        )
        return 2
    if st == "blocked":
        print(
            f"Error: {pane_id} is blocked (trust/auth/permission dialog) — a "
            f"human must answer it first (herdr agent focus <name>); typing the "
            f"task now would submit garbage into the dialog.",
            file=sys.stderr,
        )
        return 3
    # idle / done / unknown (validly reported) are safe to deliver to.
    print(st)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
