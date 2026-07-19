#!/usr/bin/env python3
"""Behavioral tests for broadcast.sh against a fake `herdr` CLI.

Covers:
  P2.6 - name+pane aliases resolving to the same pane must not double-send.
  P1.1 - a pane already `working` before the broadcast must be rejected,
         not silently waited on as if this broadcast made it busy. A pane
         that is `blocked` (trust/auth dialog) must be rejected too — typing
         a task into that dialog would submit garbage, not reach the agent.

Run directly (stdlib unittest only):
    python3 -m unittest discover -s skills/herdr-agent-comms/tests -p 'test_*.py'
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
FAKE_BIN = HERE / "bin"
BROADCAST = SCRIPTS / "broadcast.sh"


class FakeHerdrHarness:
    def __init__(self):
        self.tmpdir = tempfile.mkdtemp(prefix="hac_bcast_test_")
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

    def set_pane(self, pane_id, status, text, name=None, fail_run=False,
                 fail_get=False, malformed_get=False):
        state = self.read_state()
        state["panes"][pane_id] = {
            "agent_status": status,
            "text": text,
            "name": name,
            "fail_run": fail_run,
            "fail_get": fail_get,
            "malformed_get": malformed_get,
        }
        self.write_state(state)

    def set_status(self, pane_id, status):
        state = self.read_state()
        state["panes"][pane_id]["agent_status"] = status
        self.write_state(state)

    def append_text(self, pane_id, text):
        state = self.read_state()
        state["panes"][pane_id]["text"] += text
        self.write_state(state)

    def count_pane_run_invocations(self, pane_id):
        state = self.read_state()
        text = state["panes"][pane_id]["text"]
        return text.count("$ ")

    def run_broadcast(self, msg, targets, timeout=8, env_extra=None):
        env = dict(self.env)
        env["HAC_TIMEOUT"] = str(timeout - 2)
        if env_extra:
            env.update(env_extra)
        cmd = ["bash", str(BROADCAST), msg] + list(targets)
        return subprocess.run(cmd, env=env, text=True, capture_output=True, timeout=timeout + 15)


class BroadcastDedupeTests(unittest.TestCase):
    def setUp(self):
        self.h = FakeHerdrHarness()

    def test_name_and_pane_alias_send_only_once(self):
        """P2.6: 'reviewer' and its own pane id 'p1' both resolve to pane p1
        — broadcast must send exactly once, not twice."""
        self.h.set_pane("p1", "idle", "boot complete\n", name="reviewer")

        def finish_quickly():
            time.sleep(0.3)
            self.h.set_status("p1", "working")
            time.sleep(0.2)
            st = self.h.read_state()
            sent_text = st["panes"]["p1"]["text"]
            # Extract the marker suffix from the sent task text and echo the
            # joined marker back, as a real agent's reply would.
            m = re.search(r"HERDR_DONE_ and (\S+)", sent_text)
            if m:
                self.h.append_text("p1", f"HERDR_DONE_{m.group(1)}\n")
            self.h.set_status("p1", "idle")

        t = threading.Thread(target=finish_quickly)
        t.start()
        cp = self.h.run_broadcast("do the thing", ["reviewer", "p1"], timeout=6)
        t.join()

        sends = self.h.count_pane_run_invocations("p1")
        self.assertEqual(sends, 1, msg=f"expected exactly 1 send, got {sends}. stdout={cp.stdout!r} stderr={cp.stderr!r}")
        self.assertIn("skipping duplicate", cp.stderr.lower())

    def test_already_working_pane_is_rejected_not_sent(self):
        """P1.1: a pane that is already `working` before broadcast starts
        must be skipped, never sent to (can't distinguish its completion
        from a send this broadcast never made)."""
        self.h.set_pane("busy1", "working", "prior task in flight\n", name="busy")
        self.h.set_pane("idle1", "idle", "ready\n", name="ready")

        def finish_ready():
            time.sleep(0.2)
            st = self.h.read_state()
            sent_text = st["panes"]["idle1"]["text"]
            m = re.search(r"HERDR_DONE_ and (\S+)", sent_text)
            if m:
                self.h.append_text("idle1", f"HERDR_DONE_{m.group(1)}\n")
            self.h.set_status("idle1", "idle")

        t = threading.Thread(target=finish_ready)
        t.start()
        cp = self.h.run_broadcast("do the thing", ["busy", "ready"], timeout=6)
        t.join()

        # busy pane must never have received a pane run (no new "$ " line)
        busy_sends = self.h.count_pane_run_invocations("busy1")
        self.assertEqual(busy_sends, 0, msg=f"busy pane should not be sent to. stdout={cp.stdout!r}")
        self.assertIn("already working", cp.stderr.lower())
        # overall exit must be non-zero since a target was skipped
        self.assertNotEqual(cp.returncode, 0)
        # the ready pane should still be reported as settled
        self.assertIn("ready", cp.stdout)

    def test_all_busy_exits_error_with_nothing_sent(self):
        self.h.set_pane("busy1", "working", "prior\n", name="busy")
        cp = self.h.run_broadcast("do the thing", ["busy"], timeout=4)
        self.assertNotEqual(cp.returncode, 0)
        self.assertEqual(self.h.count_pane_run_invocations("busy1"), 0)

    def test_blocked_pane_is_rejected_not_sent(self):
        """P1.1: a pane showing `blocked` (trust/auth dialog) must be
        skipped, never sent to — typing a task into the dialog would submit
        garbage to the prompt, not reach the agent."""
        self.h.set_pane("dlg1", "blocked", "Do you trust this workspace? [y/n]\n", name="gated")
        self.h.set_pane("idle1", "idle", "ready\n", name="ready")

        def finish_ready():
            time.sleep(0.2)
            st = self.h.read_state()
            sent_text = st["panes"]["idle1"]["text"]
            m = re.search(r"HERDR_DONE_ and (\S+)", sent_text)
            if m:
                self.h.append_text("idle1", f"HERDR_DONE_{m.group(1)}\n")
            self.h.set_status("idle1", "idle")

        t = threading.Thread(target=finish_ready)
        t.start()
        cp = self.h.run_broadcast("do the thing", ["gated", "ready"], timeout=6)
        t.join()

        # blocked pane must never have received a pane run (no new "$ " line)
        blocked_sends = self.h.count_pane_run_invocations("dlg1")
        self.assertEqual(blocked_sends, 0, msg=f"blocked pane should not be sent to. stdout={cp.stdout!r}")
        self.assertIn("blocked", cp.stderr.lower())
        self.assertNotEqual(cp.returncode, 0)
        self.assertIn("ready", cp.stdout)

    def test_all_blocked_exits_error_with_nothing_sent(self):
        self.h.set_pane("dlg1", "blocked", "trust dialog\n", name="gated")
        cp = self.h.run_broadcast("do the thing", ["gated"], timeout=4)
        self.assertNotEqual(cp.returncode, 0)
        self.assertEqual(self.h.count_pane_run_invocations("dlg1"), 0)

    def test_failed_status_lookup_is_rejected_not_sent(self):
        """P2 round 6: a pane whose `herdr pane get` FAILS during the status
        preflight must be rejected, not treated as an empty (safe) status.
        Otherwise a working/blocked pane whose state can't be confirmed would
        be sent to (fail-open)."""
        self.h.set_pane("bad1", "idle", "resolves but status get fails\n",
                        name="flaky", fail_get=True)
        cp = self.h.run_broadcast("do the thing", ["flaky"], timeout=4)
        # never sent, error exit, and the reason is surfaced.
        self.assertEqual(self.h.count_pane_run_invocations("bad1"), 0,
                         msg=f"unverifiable pane must not be sent to. stdout={cp.stdout!r}")
        self.assertNotEqual(cp.returncode, 0)
        self.assertIn("verify", cp.stderr.lower())

    def test_malformed_status_response_is_rejected_not_sent(self):
        """A 0-exit but unparseable `herdr pane get` must also be rejected,
        not fall through as empty/safe."""
        self.h.set_pane("bad1", "idle", "resolves but status is garbage\n",
                        name="garbled", malformed_get=True)
        cp = self.h.run_broadcast("do the thing", ["garbled"], timeout=4)
        self.assertEqual(self.h.count_pane_run_invocations("bad1"), 0,
                         msg=f"malformed-status pane must not be sent to. stdout={cp.stdout!r}")
        self.assertNotEqual(cp.returncode, 0)

    def test_offenum_numeric_status_is_rejected_not_sent(self):
        """Regression (round 10, finding #1): a 0-exit `herdr pane get` that
        reports an off-enum status VALUE (numeric 123) must be rejected as
        unverifiable, NOT accepted as a truthy 'sendable' status. The old
        `agent_status or "unknown"` let 123 fall into the idle/done/unknown
        branch and the task was sent. fake_herdr passes the status straight
        through json.dumps, so this injects a genuine numeric status."""
        self.h.set_pane("bad1", 123, "off-enum numeric status\n", name="weird")
        cp = self.h.run_broadcast("do the thing", ["weird"], timeout=4)
        self.assertEqual(self.h.count_pane_run_invocations("bad1"), 0,
                         msg=f"off-enum-status pane must not be sent to. stdout={cp.stdout!r}")
        self.assertNotEqual(cp.returncode, 0)
        self.assertIn("verify", cp.stderr.lower())

    def test_failed_status_lookup_skips_only_bad_target(self):
        """A verifiable idle pane alongside an unverifiable one: the good pane
        still gets the message; the bad one is skipped. AND the overall exit is
        non-zero — a mixed bad+good broadcast must NOT report success just
        because the good pane went through (P3 round 6/7: `unverifiable` was
        omitted from the final aggregation, so mixed broadcasts returned 0)."""
        self.h.set_pane("bad1", "idle", "status get fails\n", name="flaky", fail_get=True)
        self.h.set_pane("ok1", "idle", "ready\n", name="ready")

        def finish_ready():
            # Poll for the send (timing isn't fixed — the fail_get target adds
            # preflight latency), then reply with the joined marker so the good
            # pane's waiter settles cleanly (rc 0). This is important for THIS
            # test: the good pane MUST complete successfully so the only reason
            # the broadcast can exit non-zero is the unverifiable aggregation.
            deadline = time.time() + 6
            m = None
            while time.time() < deadline and m is None:
                m = re.search(r"HERDR_DONE_ and (\S+)", self.h.read_state()["panes"]["ok1"]["text"])
                if m is None:
                    time.sleep(0.02)
            if m:
                self.h.append_text("ok1", f"HERDR_DONE_{m.group(1)}\n")
            self.h.set_status("ok1", "idle")

        t = threading.Thread(target=finish_ready)
        t.start()
        cp = self.h.run_broadcast("do the thing", ["flaky", "ready"], timeout=8)
        t.join()
        # good pane got the message and settled...
        self.assertGreaterEqual(self.h.count_pane_run_invocations("ok1"), 1)
        self.assertIn("ready", cp.stdout)
        # ...bad pane was skipped...
        self.assertEqual(self.h.count_pane_run_invocations("bad1"), 0)
        # ...and DESPITE the good pane succeeding, the mixed result is a FAILURE
        # (the unverifiable target must fold into the exit status, not vanish).
        self.assertNotEqual(cp.returncode, 0,
                            msg=f"mixed unverifiable+good must exit non-zero. stderr={cp.stderr!r}")


class BroadcastPartialFailureTests(unittest.TestCase):
    """P2.1: if a later pane's `pane run` fails mid fan-out, panes already
    dispatched must still be waited on and reported, not silently abandoned.
    """

    def setUp(self):
        self.h = FakeHerdrHarness()

    def test_later_send_failure_does_not_abandon_earlier_dispatch(self):
        self.h.set_pane("ok1", "idle", "ready\n", name="first")
        self.h.set_pane("bad1", "idle", "ready\n", name="second", fail_run=True)

        def finish_first():
            # Poll for the send (not a fixed sleep): preflight/baseline work
            # ahead of Phase 3 dispatch means the exact send timing isn't
            # fixed, so wait for the marker to actually appear in the task
            # text before echoing the reply.
            deadline = time.time() + 5
            m = None
            while time.time() < deadline and m is None:
                sent_text = self.h.read_state()["panes"]["ok1"]["text"]
                m = re.search(r"HERDR_DONE_ and (\S+)", sent_text)
                if m is None:
                    time.sleep(0.02)
            if m:
                self.h.append_text("ok1", f"HERDR_DONE_{m.group(1)}\n")
            self.h.set_status("ok1", "idle")

        t = threading.Thread(target=finish_first)
        t.start()
        cp = self.h.run_broadcast("do the thing", ["first", "second"], timeout=6)
        t.join()

        # The first pane was sent to and must still be waited on / reported.
        self.assertEqual(self.h.count_pane_run_invocations("ok1"), 1)
        self.assertIn("first", cp.stdout)
        self.assertIn("idle/done", cp.stdout)
        # The second pane's send failed and must be surfaced, not silently dropped.
        self.assertIn("send-failed", cp.stderr.lower())
        self.assertIn("partial results", cp.stderr.lower())
        self.assertNotEqual(cp.returncode, 0)

    def test_first_send_failure_still_waits_on_later_dispatched_panes(self):
        self.h.set_pane("bad1", "idle", "ready\n", name="first", fail_run=True)
        self.h.set_pane("ok1", "idle", "ready\n", name="second")

        def finish_second():
            deadline = time.time() + 5
            m = None
            while time.time() < deadline and m is None:
                sent_text = self.h.read_state()["panes"]["ok1"]["text"]
                m = re.search(r"HERDR_DONE_ and (\S+)", sent_text)
                if m is None:
                    time.sleep(0.02)
            if m:
                self.h.append_text("ok1", f"HERDR_DONE_{m.group(1)}\n")
            self.h.set_status("ok1", "idle")

        t = threading.Thread(target=finish_second)
        t.start()
        cp = self.h.run_broadcast("do the thing", ["first", "second"], timeout=6)
        t.join()

        self.assertEqual(self.h.count_pane_run_invocations("ok1"), 1)
        self.assertIn("second", cp.stdout)
        self.assertIn("idle/done", cp.stdout)
        self.assertNotEqual(cp.returncode, 0)


if __name__ == "__main__":
    unittest.main()
