#!/usr/bin/env python3
"""Behavioral tests for broadcast.sh against a fake `tmux` CLI.

Run:
    python3 -m unittest discover -s skills/tmux-agent-comms/tests -p 'test_*.py'
"""

from __future__ import annotations

import json
import os
import re
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
BROADCAST = SCRIPTS / "broadcast.sh"


class FakeTmuxHarness:
    def __init__(self):
        self.tmpdir = tempfile.mkdtemp(prefix="tac_bcast_")
        self.state_path = os.path.join(self.tmpdir, "state.json")
        self.write_state({"sessions": {}})
        self.env = dict(os.environ)
        self.env["FAKE_TMUX_STATE"] = self.state_path
        self.env["PATH"] = f"{FAKE_BIN}{os.pathsep}{self.env.get('PATH', '')}"
        self.env["TAC_TIMEOUT"] = "3"
        # Keep waiter snappy under test.
        self.env["TAC_WAIT_ARGS"] = "--interval 0.1 --quiet-cycles 2"

    def write_state(self, state):
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(state, f)

    def read_state(self):
        with open(self.state_path, encoding="utf-8") as f:
            return json.load(f)

    def set_session(self, name, text, fail_capture=False, fail_send=False):
        state = self.read_state()
        state["sessions"][name] = {
            "text": text,
            "fail_capture": fail_capture,
            "fail_send": fail_send,
        }
        self.write_state(state)

    def set_text(self, name, text):
        state = self.read_state()
        state["sessions"][name]["text"] = text
        self.write_state(state)

    def run_broadcast(self, msg, *sessions, timeout=20):
        cmd = ["bash", str(BROADCAST), msg, *sessions]
        return subprocess.run(
            cmd, env=self.env, text=True, capture_output=True, timeout=timeout
        )


class BroadcastTests(unittest.TestCase):
    def setUp(self):
        self.h = FakeTmuxHarness()

    def test_missing_session_fails_early(self):
        self.h.set_session("a", "idle\n")
        cp = self.h.run_broadcast("hi", "a", "missing")
        self.assertNotEqual(cp.returncode, 0)
        self.assertIn("don't exist", cp.stderr)

    def test_skips_blocked_and_fails(self):
        self.h.set_session("ok", "ready>\n")
        self.h.set_session("bad", "Do you trust the files in this folder?\n")
        # ok will get a send; complete it with the marker the send injects.
        def complete():
            # Poll until send appends task text, then inject joined marker.
            for _ in range(40):
                text = self.h.read_state()["sessions"]["ok"]["text"]
                m = re.search(r"TAC_DONE_ and (\S+)", text)
                if m:
                    joined = f"TAC_DONE_{m.group(1)}"
                    self.h.set_text("ok", text + f"\nreply\n{joined}\n")
                    return
                time.sleep(0.05)

        threading.Thread(target=complete, daemon=True).start()
        cp = self.h.run_broadcast("do work", "ok", "bad")
        self.assertNotEqual(cp.returncode, 0)
        self.assertIn("blocked", cp.stderr.lower())
        self.assertIn("ok", cp.stdout)

    def test_skips_working(self):
        self.h.set_session("busy", "working\nesc to interrupt\n")
        cp = self.h.run_broadcast("hi", "busy")
        self.assertNotEqual(cp.returncode, 0)
        self.assertIn("working", cp.stderr.lower())

    def test_success_with_marker(self):
        self.h.set_session("r1", "ready>\n")
        self.h.set_session("r2", "ready>\n")

        def complete_all():
            done = set()
            for _ in range(80):
                state = self.h.read_state()
                for name in ("r1", "r2"):
                    if name in done:
                        continue
                    text = state["sessions"][name]["text"]
                    m = re.search(r"TAC_DONE_ and (\S+)", text)
                    if m:
                        joined = f"TAC_DONE_{m.group(1)}"
                        self.h.set_text(name, text + f"\nok from {name}\n{joined}\n")
                        done.add(name)
                if len(done) == 2:
                    return
                time.sleep(0.05)

        threading.Thread(target=complete_all, daemon=True).start()
        cp = self.h.run_broadcast("pull main", "r1", "r2")
        self.assertEqual(cp.returncode, 0, msg=f"stdout={cp.stdout}\nstderr={cp.stderr}")
        self.assertIn("r1", cp.stdout)
        self.assertIn("r2", cp.stdout)

    def test_dedupes_targets(self):
        self.h.set_session("only", "ready>\n")

        def complete():
            for _ in range(40):
                text = self.h.read_state()["sessions"]["only"]["text"]
                # Count how many TAC_DONE split instructions landed.
                matches = re.findall(r"TAC_DONE_ and (\S+)", text)
                if matches:
                    # Complete with the last (only should be one after dedupe).
                    joined = f"TAC_DONE_{matches[-1]}"
                    self.h.set_text("only", text + f"\ndone\n{joined}\n")
                    return
                time.sleep(0.05)

        threading.Thread(target=complete, daemon=True).start()
        cp = self.h.run_broadcast("hi", "only", "only")
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("already targeted", cp.stderr)


if __name__ == "__main__":
    unittest.main()
