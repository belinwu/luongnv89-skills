---
name: tmux-agent-comms
description: "Manage AI agents in tmux: spawn sessions, send messages, wait, capture replies, inspect fleets, and tear down safely. Use for tmux-hosted CLI agents. Don't use for SSH, GNU screen, or GUI apps."
license: MIT
compatibility: "Requires `tmux` on PATH. Optional Python 3 for wait/preflight/broadcast helpers."
effort: medium
metadata:
  version: 2.1.0
  author: "Luong NGUYEN <luongnv89@gmail.com>"
---

# Tmux Agent Comms

Manage CLI agents in separate tmux sessions. Treat each session as one agent; orchestrate it with `send-keys` and `capture-pane`. Relay reply deltas instead of whole screens to protect the context/token budget.

New sessions open in a terminal tab inside the current app by default. If the environment cannot open one, create the session detached and print the exact attach command. Never invoke `attach-session` from a non-TTY tool.

Use `herdr-agent-comms` instead when agents live in Herdr.

## When to Use

Route directly to the required mode; do not read unrelated references.

| Task | Start |
|---|---|
| Spawn an agent | Phase 1 |
| Message or steer an existing agent | Phase 2 |
| Read a pane, show status, or inspect | Phase 5 |
| Broadcast to a fleet | Phase 6 |
| Shut down an agent | Phase 6 |

## Prerequisites

1. Run `command -v tmux`; stop with installation guidance if it fails.
2. Resolve helper scripts using `references/tmux-recipes.md` when messaging, waiting, or broadcasting.
3. Confirm the exact session and inspect its pane before writing to it.

## Critical Rules

1. **Confirm destructive actions.** Never send `exit`/`/quit`, kill a session, or kill the server without explicit approval.
2. **Fail closed before every send.** Only preflight exit 0 is sendable. Exit 2 means working, 3 blocked, and 4 unverifiable.
3. **Use a fresh proof cycle.** Every message needs a new baseline file and split completion marker. Never reuse either for a follow-up.
4. **Send text and Enter separately.** For multiline/code-heavy text, use tmux paste-buffer; see `references/tmux-recipes.md`.
5. **Bound waiting.** Use a wall-clock cap or at most 2–3 re-waits. Surface a stall instead of polling forever.
6. **Keep reads bounded.** Start with `capture-pane -S -40` and widen only when the reply is truncated.
7. **Escalate blocked panes.** A trust/auth/permission dialog requires a human; do not type task text into it.

## Workflow

Run the six phases in order for a send. A read-only status/inspect operation may jump to Phase 5.

### Phase 1 — Create or Discover

List sessions:

```bash
tmux list-sessions 2>/dev/null || echo "no tmux server running yet"
```

Name new sessions `<folder>-<short-task>` (for example, `myrepo-reviewer`). Avoid collisions with `tmux has-session` before creating one. Launch the requested interactive CLI in a new app terminal tab; if no tab facility exists, use detached mode and print `tmux attach-session -t <name>` for the human.

After spawn, require readiness before assigning work:

```bash
python3 "$here/wait_for_idle.py" "$name" --ready --timeout 60 --no-print
```

Exit 0 is ready, 3 is blocked, 2 is timeout, and 1 is error. Spawn fleets first, then check readiness concurrently. Read `references/tmux-recipes.md` for naming, tab/detached branches, script resolution, and fleet readiness.

**Complete when:** every created session has an exact name and passes the ready gate, or the failure is surfaced without sending work.

### Phase 2 — Resolve the Exact Target

```bash
tmux has-session -t "$target" 2>/dev/null
```

If missing, list sessions and ask on ambiguity; never guess. Use `session:window.pane` for a specific pane.

**Complete when:** one existing tmux target is confirmed.

### Phase 3 — Baseline, Preflight, and Send

Read `references/delivery-and-waiting.md` before sending. Follow its contract:

1. Capture `-S -80` to a temporary baseline file.
2. Mint a fresh suffix and define `completion_marker="TAC_DONE_$suffix"`.
3. Append an instruction that prints `TAC_DONE_` joined with the suffix only after completion.
4. Run `preflight_send.py` immediately before dispatch; send only on exit 0.
5. Send message text, then send `Enter` in a separate call.
6. Check once for post-send activity against the baseline. If unchanged, re-preflight before one recovery Enter; fail if still unchanged.

On multiline/code-heavy input, use paste-buffer rather than shell escaping. Always clean up temporary files on failure.

**Complete when:** post-send activity proves delivery, or a descriptive failure is surfaced. Typed text alone is not proof.

### Phase 4 — Wait and Verify

```bash
python3 "$here/wait_for_idle.py" "$target" --timeout 180 --scrollback 80 \
  --baseline-file "$baseline_file" --completion-marker "$completion_marker"
rc=$?
rm -f "$baseline_file"
```

Handle exit 0 as settled, 1 as error, 2 as timeout, and 3 as blocked. Before relaying an actionable result, independently compare two short capped-tail captures. Changing output/spinner means working; unchanged output without completion means stalled.

Read `references/delivery-and-waiting.md` for delivery recovery, wait modes, advisory verdicts, and the anti-deadloop budget.

**Complete when:** a fresh marker and independent bounded read verify the reply, or the bounded wait ends with an explicit state.

### Phase 5 — Read, Status, or Inspect

Read a reply with:

```bash
tmux capture-pane -t "$target" -p -S -40
```

Widen stepwise if capture starts mid-sentence; use unbounded scrollback only as a last resort. Relay substantive lines, not TUI chrome or old turns.

For **status**, remain read-only and report: agent ID, exact session, state (`in-progress`, `done`, `blocked`, `unknown`), short progress, start time, and workdir. For **inspect**, resolve one exact session, include a bounded tail and pane details, then print—but do not run—the human attach command.

Read `references/tmux-recipes.md` for classification commands, periodic fleet status, scrollback, and troubleshooting.

**Complete when:** the requested reply or status is concise, target-specific, and not truncated.

### Phase 6 — Continue, Broadcast, or Tear Down

- **Continue:** restart Phase 3 with a fresh baseline and marker.
- **Broadcast:** run `"$here/broadcast.sh" "<message>" <session...>`; it preflights, sends first, then waits concurrently. Do not serialize send/wait by agent.
- **Long fleet run:** emit a read-only status table about every five minutes within the same overall wait budget.
- **Tear down:** after explicit confirmation, prefer `tmux kill-session -t <name>` over `tmux kill-server`.

**Complete when:** every follow-up has an independent proof cycle, broadcast failures are reported per target, or confirmed teardown affects only named sessions.

## Acceptance Criteria

- Every write targets a confirmed session and immediately follows a successful preflight.
- Every message has a fresh baseline, split marker, delivery check, bounded wait, and independent capped-tail verification.
- No blocked dialog receives task text; no destructive command runs without confirmation.
- Fleet sends and readiness checks run concurrently, with partial failures identified by session.
- The expected output is the requested reply/status plus the adapted Step Completion Report below—not raw unbounded scrollback.

## Example

```bash
target=reviewer
tmux has-session -t "$target" 2>/dev/null || { echo "Error: missing $target" >&2; exit 1; }
# Resolve $here, then follow references/delivery-and-waiting.md for the
# baseline → preflight → send → delivery → wait → verify cycle.
```

Expected result: the agent's new reply is relayed, the joined marker proves this turn completed, and the report records each gate.

## Edge Cases

- Duplicate name: choose a collision-free name before spawn.
- Trust/auth prompt: exit 3; show it to the human and stop.
- Message unchanged after recovery Enter: report not delivered; do not start the reply wait.
- Timeout or stable pane without completion: surface working vs stalled after a bounded independent read.
- Follow-up: never reuse a deleted baseline or marker already present in transcript.
- Truncated capture: widen `-S` stepwise.
- Human attached manually: detach with `Ctrl-b d`; never kill merely to return control.

## References

- `references/delivery-and-waiting.md` — read for any send/wait cycle, recovery, marker contract, or timeout.
- `references/tmux-recipes.md` — read only for script resolution, spawn modes, fleets, status/inspect, multiline sends, attach, scrollback, or troubleshooting.
- `scripts/preflight_send.py` — fail-closed check before every send or recovery Enter.
- `scripts/wait_for_idle.py` — readiness and settled-reply waiter.
- `scripts/broadcast.sh` — safe concurrent fleet broadcast.

## Step Completion Report

After each operation, emit only applicable rows:

```text
◆ Tmux Agent Comms ([operation])
··································································
  Target resolved:     √ pass ([exact session])
  Preflight:           √ pass (idle)
  Baseline captured:   √ pass
  Message delivered:   √ pass (activity vs baseline)
  Completion marker:   √ pass (fresh and joined)
  Reply verified:      √ pass (bounded independent read)
  Destructive action:  — none (or: √ confirmed)
  Result:              PASS | FAIL | PARTIAL
```

For spawn, report `Session created` and `Ready gate`; for status, report `Read-only`; for teardown, report `Confirmed` and `Session killed`. Use `⚠` for recovered delivery or an escalated stall.
