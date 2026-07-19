#!/usr/bin/env python3
"""Behavioral tests for wait_for_idle.py against a fake `herdr` CLI.

Covers the P1.1/P2.7 false-completion fix: a pane already `working` (or
already carrying the completion marker) before this send must not be
reported as settled for THIS send.

Run directly (stdlib unittest only):
    python3 -m unittest discover -s skills/herdr-agent-comms/tests -p 'test_*.py'
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
FAKE_BIN = HERE / "bin"
WAITER = SCRIPTS / "wait_for_idle.py"


class FakeHerdrHarness:
    def __init__(self):
        self.tmpdir = tempfile.mkdtemp(prefix="hac_test_")
        self.state_path = os.path.join(self.tmpdir, "state.json")
        self.write_state({"panes": {}})
        self.env = dict(os.environ)
        self.env["FAKE_HERDR_STATE"] = self.state_path
        self.env["PATH"] = f"{FAKE_BIN}{os.pathsep}{self.env.get('PATH', '')}"

    def write_state(self, state):
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(state, f)

    def read_state(self):
        with open(self.state_path, encoding="utf-8") as f:
            return json.load(f)

    def set_pane(self, pane_id, status, text, name=None):
        state = self.read_state()
        state["panes"][pane_id] = {"agent_status": status, "text": text, "name": name}
        self.write_state(state)

    def set_status(self, pane_id, status):
        state = self.read_state()
        state["panes"][pane_id]["agent_status"] = status
        self.write_state(state)

    def delete_pane(self, pane_id):
        state = self.read_state()
        state["panes"].pop(pane_id, None)
        self.write_state(state)

    def append_text(self, pane_id, text):
        state = self.read_state()
        state["panes"][pane_id]["text"] += text
        self.write_state(state)

    def baseline_file(self, text):
        p = os.path.join(self.tmpdir, f"baseline_{time.time_ns()}.txt")
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
        return p

    def run_waiter(self, pane_id, *extra_args, timeout=5):
        cmd = [sys.executable, str(WAITER), pane_id, "--timeout", str(timeout)]
        cmd.extend(extra_args)
        return subprocess.run(cmd, env=self.env, text=True, capture_output=True, timeout=timeout + 10)


class WaitForIdleMarkerSemanticsTests(unittest.TestCase):
    def setUp(self):
        self.h = FakeHerdrHarness()

    def test_stale_marker_in_baseline_is_not_success(self):
        """P2.7: a marker already present in the pre-send baseline (leftover
        from a previous task) must not be accepted as proof THIS send
        finished — the pane should time out waiting for a *fresh* marker.
        """
        marker = "HERDR_DONE_stale123"
        pane_text = f"previous task output\n{marker}\n"
        self.h.set_pane("p1", "idle", pane_text)
        baseline = self.h.baseline_file(pane_text)  # baseline == current text (marker included)

        cp = self.h.run_waiter(
            "p1", "--baseline-file", baseline, "--completion-marker", marker, "--timeout", "1"
        )
        self.assertEqual(cp.returncode, 2, msg=f"stdout={cp.stdout!r} stderr={cp.stderr!r}")

    def test_prior_working_pane_does_not_falsely_complete_this_send(self):
        """P1.1: pane is ALREADY working (prior task in flight) when the
        waiter starts. Baseline was captured while working. No fresh marker
        ever appears. The waiter must NOT report success — it must time out,
        not short-circuit on a stale `saw_working` transition.
        """
        prior_text = "prior task still running...\n"
        self.h.set_pane("p1", "working", prior_text)
        baseline = self.h.baseline_file(prior_text)
        marker = "HERDR_DONE_thissend456"

        # Pane flips to idle shortly after (prior task finishes) but the
        # fresh marker for THIS send never shows up.
        def flip():
            time.sleep(0.3)
            self.h.set_status("p1", "idle")

        t = threading.Thread(target=flip)
        t.start()
        cp = self.h.run_waiter(
            "p1", "--baseline-file", baseline, "--completion-marker", marker, "--timeout", "1"
        )
        t.join()
        self.assertEqual(cp.returncode, 2, msg=f"stdout={cp.stdout!r} stderr={cp.stderr!r}")

    def test_fresh_marker_after_working_is_success(self):
        """Sanity/control: once the fresh marker actually appears after a
        real working transition, the waiter must succeed (rc 0)."""
        baseline_text = "before send\n"
        self.h.set_pane("p1", "idle", baseline_text)
        baseline = self.h.baseline_file(baseline_text)
        marker = "HERDR_DONE_real789"

        def do_work():
            time.sleep(0.1)
            self.h.set_status("p1", "working")
            time.sleep(0.2)
            self.h.append_text("p1", f"reply text {marker}\n")
            self.h.set_status("p1", "idle")

        t = threading.Thread(target=do_work)
        t.start()
        cp = self.h.run_waiter(
            "p1", "--baseline-file", baseline, "--completion-marker", marker, "--timeout", "5"
        )
        t.join()
        self.assertEqual(cp.returncode, 0, msg=f"stdout={cp.stdout!r} stderr={cp.stderr!r}")
        self.assertIn(marker, cp.stdout)

    def test_working_to_done_transition_is_success_not_timeout(self):
        """Regression (P2 round 4): a pane that goes working -> DONE and stays
        `done` (never `idle`) must be reported as finished (rc 0), not time out
        (rc 2). The old working-branch waited for `done` in only HALF the slice
        then spent the WHOLE remaining deadline waiting only for `idle`, so a
        pane settling on `done` AFTER that half-window blocked until timeout.
        The fix bounds the idle-wait too and loops back to re-check either
        terminal state.

        Timing matters: the pane must stay `working` past the first half-window
        (~half the deadline) and only then flip to `done`, otherwise the old
        code's initial `wait done` succeeds and the bug never triggers. With a
        2s deadline the half-window is ~1s, so flip at 1.2s.
        """
        baseline_text = "before send\n"
        self.h.set_pane("p1", "working", baseline_text)
        baseline = self.h.baseline_file(baseline_text)

        def do_work():
            time.sleep(1.2)  # past the first half-window; misses the buggy `wait done`
            self.h.append_text("p1", "reply text, task complete\n")
            self.h.set_status("p1", "done")  # terminal DONE, never idle

        t = threading.Thread(target=do_work)
        t.start()
        cp = self.h.run_waiter("p1", "--baseline-file", baseline, "--timeout", "2")
        t.join()
        self.assertEqual(cp.returncode, 0, msg=f"stdout={cp.stdout!r} stderr={cp.stderr!r}")

    def test_working_to_done_with_marker_is_success(self):
        """Same working->done transition (flipping past the half-window), but
        with a completion marker: the fresh marker appearing at the `done`
        transition must be accepted, not lost because the branch only watched
        for `idle`."""
        baseline_text = "before send\n"
        self.h.set_pane("p1", "working", baseline_text)
        baseline = self.h.baseline_file(baseline_text)
        marker = "HERDR_DONE_done_only_42"

        def do_work():
            time.sleep(1.2)
            self.h.append_text("p1", f"reply {marker}\n")
            self.h.set_status("p1", "done")  # terminal DONE, never idle

        t = threading.Thread(target=do_work)
        t.start()
        cp = self.h.run_waiter(
            "p1", "--baseline-file", baseline, "--completion-marker", marker, "--timeout", "2"
        )
        t.join()
        self.assertEqual(cp.returncode, 0, msg=f"stdout={cp.stdout!r} stderr={cp.stderr!r}")
        self.assertIn(marker, cp.stdout)

    def test_pane_disappearing_mid_wait_is_error_not_completion(self):
        """Regression (P2 round 5): if the pane vanishes during the
        content-stability wait, a FAILED `herdr pane read` must not stabilize
        into a false completion (rc 0). It must surface as an error (rc 1).
        --no-status forces the content-stability path (no agent-status).
        """
        baseline_text = "task running\n"
        self.h.set_pane("p1", "working", baseline_text)
        baseline = self.h.baseline_file(baseline_text)

        def kill_pane():
            time.sleep(0.4)
            self.h.delete_pane("p1")  # pane gone: reads now fail (rc 1)

        t = threading.Thread(target=kill_pane)
        t.start()
        cp = self.h.run_waiter(
            "p1", "--baseline-file", baseline, "--no-status",
            "--interval", "0.2", "--timeout", "3",
        )
        t.join()
        self.assertEqual(cp.returncode, 1, msg=f"stdout={cp.stdout!r} stderr={cp.stderr!r}")

    def test_pane_gone_in_status_path_read_is_error_not_completion(self):
        """Same disappearance, but on the prefer-status path: pane is idle/done
        (so we take the terminal branch), then the transcript read fails. A
        failed read there must be an error (rc 1), never a success. Uses a
        pane id shaped like a real herdr id (w..:..) so resolve_pane accepts it
        and the failure happens at the transcript read, not at resolution."""
        baseline_text = "task running\n"
        self.h.set_pane("w1:p1", "working", baseline_text)
        baseline = self.h.baseline_file(baseline_text)

        def flip_then_kill():
            time.sleep(0.3)
            self.h.set_status("w1:p1", "done")  # enter terminal branch...
            time.sleep(0.05)
            self.h.delete_pane("w1:p1")          # ...then the read fails

        t = threading.Thread(target=flip_then_kill)
        t.start()
        cp = self.h.run_waiter("w1:p1", "--baseline-file", baseline, "--timeout", "3")
        t.join()
        # rc 1 (read failed) is the correct outcome; the bug returned 0.
        self.assertEqual(cp.returncode, 1, msg=f"stdout={cp.stdout!r} stderr={cp.stderr!r}")

    def test_blocked_status_returns_3(self):
        self.h.set_pane("p1", "blocked", "trust dialog\n")
        baseline = self.h.baseline_file("trust dialog\n")
        cp = self.h.run_waiter("p1", "--baseline-file", baseline, "--timeout", "1")
        self.assertEqual(cp.returncode, 3)

    def test_ready_accepts_already_idle_without_working(self):
        self.h.set_pane("p1", "idle", "already done earlier\n")
        cp = self.h.run_waiter("p1", "--ready", "--timeout", "1")
        self.assertEqual(cp.returncode, 0)

    def test_no_marker_legacy_fallback_uses_saw_working(self):
        """Without a completion marker arranged, a genuine working->idle
        transition for THIS send is still accepted (legacy behavior)."""
        baseline_text = "before\n"
        self.h.set_pane("p1", "idle", baseline_text)
        baseline = self.h.baseline_file(baseline_text)

        def do_work():
            time.sleep(0.1)
            self.h.set_status("p1", "working")
            time.sleep(0.2)
            self.h.append_text("p1", "reply without marker\n")
            self.h.set_status("p1", "idle")

        t = threading.Thread(target=do_work)
        t.start()
        cp = self.h.run_waiter("p1", "--baseline-file", baseline, "--timeout", "5")
        t.join()
        self.assertEqual(cp.returncode, 0, msg=f"stdout={cp.stdout!r} stderr={cp.stderr!r}")


if __name__ == "__main__":
    unittest.main()
