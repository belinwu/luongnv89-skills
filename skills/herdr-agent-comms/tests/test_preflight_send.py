#!/usr/bin/env python3
"""Behavioral tests for preflight_send.py against a fake `herdr` CLI.

The single-target twin of broadcast.sh Phase 1b (round 10, finding #2). Verifies
the fail-closed enum validation: only idle/done/unknown are sendable; working,
blocked, unverifiable-lookup, and OFF-ENUM values each get a distinct non-zero
exit so a caller can never type a task into a working/blocked/unverifiable pane.

Run directly (stdlib unittest only):
    python3 -m unittest discover -s skills/herdr-agent-comms/tests -p 'test_*.py'
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
FAKE_BIN = HERE / "bin"
PREFLIGHT = SCRIPTS / "preflight_send.py"


class FakeHerdrHarness:
    def __init__(self):
        self.tmpdir = tempfile.mkdtemp(prefix="hac_preflight_test_")
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

    def set_pane(self, pane_id, status, text="", name=None,
                 fail_get=False, malformed_get=False):
        state = self.read_state()
        state["panes"][pane_id] = {
            "agent_status": status, "text": text, "name": name,
            "fail_get": fail_get, "malformed_get": malformed_get,
        }
        self.write_state(state)

    def run_preflight(self, pane_id, timeout=8):
        cmd = [sys.executable, str(PREFLIGHT), pane_id]
        return subprocess.run(cmd, env=self.env, text=True, capture_output=True, timeout=timeout)


class PreflightSendTests(unittest.TestCase):
    def setUp(self):
        self.h = FakeHerdrHarness()

    def test_idle_is_sendable(self):
        self.h.set_pane("p1", "idle")
        cp = self.h.run_preflight("p1")
        self.assertEqual(cp.returncode, 0, msg=f"stderr={cp.stderr!r}")
        self.assertIn("idle", cp.stdout)

    def test_done_is_sendable(self):
        self.h.set_pane("p1", "done")
        self.assertEqual(self.h.run_preflight("p1").returncode, 0)

    def test_unknown_is_sendable(self):
        """A validly-absent status (non-integrated CLI) is still sendable."""
        self.h.set_pane("p1", "unknown")
        self.assertEqual(self.h.run_preflight("p1").returncode, 0)

    def test_working_returns_2(self):
        self.h.set_pane("p1", "working")
        cp = self.h.run_preflight("p1")
        self.assertEqual(cp.returncode, 2, msg=f"stderr={cp.stderr!r}")
        self.assertIn("working", cp.stderr.lower())

    def test_blocked_returns_3(self):
        """The reported repro: a blocked trust dialog must NOT be sendable."""
        self.h.set_pane("p1", "blocked", "Trust this workspace? [y/n]\n")
        cp = self.h.run_preflight("p1")
        self.assertEqual(cp.returncode, 3, msg=f"stderr={cp.stderr!r}")
        self.assertIn("blocked", cp.stderr.lower())

    def test_failed_lookup_returns_4_unverifiable(self):
        self.h.set_pane("p1", "idle", fail_get=True)
        cp = self.h.run_preflight("p1")
        self.assertEqual(cp.returncode, 4, msg=f"stderr={cp.stderr!r}")

    def test_malformed_lookup_returns_4_unverifiable(self):
        self.h.set_pane("p1", "idle", malformed_get=True)
        self.assertEqual(self.h.run_preflight("p1").returncode, 4)

    def test_numeric_offenum_status_returns_4_unverifiable(self):
        """finding #1 hole: a numeric 123 status must be unverifiable, not
        treated as a truthy sendable status (rc 4, not rc 0)."""
        self.h.set_pane("p1", 123)
        cp = self.h.run_preflight("p1")
        self.assertEqual(cp.returncode, 4, msg=f"stderr={cp.stderr!r}")

    def test_garbage_string_status_returns_4_unverifiable(self):
        self.h.set_pane("p1", "totally-bogus")
        self.assertEqual(self.h.run_preflight("p1").returncode, 4)

    def test_empty_string_status_returns_4_unverifiable(self):
        self.h.set_pane("p1", "")
        self.assertEqual(self.h.run_preflight("p1").returncode, 4)


if __name__ == "__main__":
    unittest.main()
