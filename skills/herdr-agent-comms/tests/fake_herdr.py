#!/usr/bin/env python3
"""Fake `herdr` CLI for tests. Not shipped as part of the skill.

State lives in a JSON file at $FAKE_HERDR_STATE, shaped:
{
  "panes": {
    "<pane_id>": {
      "agent_status": "idle|working|done|blocked|unknown",
      "text": "<current transcript>",
      "name": "<agent name or null>",
      "fail_run": true  # optional: "pane run" on this pane returns exit 1
                        # without mutating state, to simulate a dispatch
                        # failure partway through a broadcast fan-out.
    }
  }
}

Supported subcommands (only what the scripts under test call):
  pane get <id>
  pane read <id> --source ... --lines N
  pane split <id> --direction d --cwd c --no-focus
  pane rename <id> <name>
  pane run <id> <text...>
  pane send-keys <id> enter
  agent get <name-or-id>
  agent list
  agent rename <id> <name>
  wait agent-status <id> --status s --timeout ms
"""

from __future__ import annotations

import json
import os
import sys
import time


def load_state():
    path = os.environ["FAKE_HERDR_STATE"]
    # os.replace() is atomic, but a reader can still land in the brief gap
    # where the old inode was just unlinked; retry a few times rather than
    # let a concurrent writer flake the test.
    for _ in range(20):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            time.sleep(0.01)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_state(state):
    # Concurrent `herdr` invocations (broadcast waits on several panes at
    # once) can read this file mid-write; write-then-rename makes each
    # update atomic so a reader never sees a truncated/partial JSON file.
    path = os.environ["FAKE_HERDR_STATE"]
    tmp_path = f"{path}.tmp.{os.getpid()}.{id(state)}"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(state, f)
    os.replace(tmp_path, path)


def find_pane_by_id(state, pane_id):
    """`pane <verb> <id>` only accepts literal pane ids, like real herdr."""
    return pane_id if pane_id in state["panes"] else None


def find_pane(state, ident):
    """`agent <verb> <ident>` accepts a pane id OR an agent name."""
    panes = state["panes"]
    if ident in panes:
        return ident
    for pid, p in panes.items():
        if p.get("name") == ident:
            return pid
    return None


def cmd_pane_get(args):
    state = load_state()
    pid = find_pane_by_id(state, args[0])
    if pid is None:
        print(json.dumps({"error": "not found"}))
        return 1
    p = state["panes"][pid]
    print(json.dumps({"result": {"pane": {"pane_id": pid, "agent_status": p["agent_status"]}}}))
    return 0


def cmd_pane_read(args):
    state = load_state()
    pid = find_pane_by_id(state, args[0])
    if pid is None:
        print("")
        return 1
    print(state["panes"][pid]["text"])
    return 0


def cmd_pane_split(args):
    state = load_state()
    src = args[0]
    new_id = f"{src}-split{len(state['panes'])}"
    state["panes"][new_id] = {"agent_status": "unknown", "text": "", "name": None}
    save_state(state)
    print(json.dumps({"result": {"pane": {"pane_id": new_id}}}))
    return 0


def cmd_pane_rename(args):
    state = load_state()
    pid = find_pane_by_id(state, args[0])
    if pid is not None:
        state["panes"][pid]["name"] = args[1]
        save_state(state)
    print(json.dumps({"result": {}}))
    return 0


def cmd_pane_run(args):
    state = load_state()
    pid = find_pane_by_id(state, args[0])
    text = args[1] if len(args) > 1 else ""
    if pid is not None:
        if state["panes"][pid].get("fail_run"):
            print(json.dumps({"error": "simulated pane run failure"}), file=sys.stderr)
            return 1
        state["panes"][pid]["agent_status"] = "working"
        state["panes"][pid]["text"] += f"\n$ {text}\n"
        save_state(state)
    print(json.dumps({"result": {}}))
    return 0


def cmd_pane_send_keys(args):
    print(json.dumps({"result": {}}))
    return 0


def cmd_agent_get(args):
    state = load_state()
    pid = find_pane(state, args[0])
    if pid is None:
        print(json.dumps({"error": "not found"}))
        return 1
    print(json.dumps({"result": {"agent": {"pane_id": pid}}}))
    return 0


def cmd_agent_list(_args):
    state = load_state()
    agents = [
        {"name": p.get("name"), "pane_id": pid, "terminal_id": pid}
        for pid, p in state["panes"].items()
    ]
    print(json.dumps({"result": {"agents": agents}}))
    return 0


def cmd_agent_rename(args):
    return cmd_pane_rename(args)


def cmd_wait_agent_status(args):
    pid = args[0]
    status = None
    timeout_ms = 1000
    it = iter(args[1:])
    for a in it:
        if a == "--status":
            status = next(it)
        elif a == "--timeout":
            timeout_ms = int(next(it))
    deadline = time.time() + timeout_ms / 1000.0
    while time.time() < deadline:
        state = load_state()
        rpid = find_pane(state, pid)
        if rpid is not None and state["panes"][rpid]["agent_status"] == status:
            return 0
        time.sleep(0.02)
    return 1


def main(argv):
    if not argv:
        return 1
    group = argv[0]
    if group == "pane":
        sub = argv[1]
        rest = argv[2:]
        if sub == "get":
            return cmd_pane_get(rest)
        if sub == "read":
            return cmd_pane_read(rest)
        if sub == "split":
            return cmd_pane_split(rest)
        if sub == "rename":
            return cmd_pane_rename(rest)
        if sub == "run":
            return cmd_pane_run(rest)
        if sub == "send-keys":
            return cmd_pane_send_keys(rest)
    elif group == "agent":
        sub = argv[1]
        rest = argv[2:]
        if sub == "get":
            return cmd_agent_get(rest)
        if sub == "list":
            return cmd_agent_list(rest)
        if sub == "rename":
            return cmd_agent_rename(rest)
    elif group == "wait":
        sub = argv[1]
        rest = argv[2:]
        if sub == "agent-status":
            return cmd_wait_agent_status(rest)
    print(f"fake_herdr: unhandled command: {argv}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
