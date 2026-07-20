---
name: tmux-agent-comms
description: "Manage AI agents in tmux: spawn sessions in current app terminal tabs by default; message CLI agents via send-keys/capture-pane; read replies; kill sessions. Use to launch fleets or talk to running agents. Don't use for SSH, screen, or GUI apps."
license: MIT
effort: medium
metadata:
  version: 2.0.0
  author: "Luong NGUYEN <luongnv89@gmail.com>"
compatibility: "Requires `tmux` on PATH. Optional Python 3 for wait/preflight/broadcast helpers."
---

# Tmux Agent Comms

Manage and talk to AI agents (another Claude Code, Gemini CLI, Codex, pi, OpenCode, or any CLI) running in separate tmux sessions: **create** sessions, **send** messages, **wait** for the agent to finish, **capture** replies, **check status**, **inspect** sessions, and **tear down** when done.

Default spawn behavior: each new tmux session opens in a **new terminal tab inside the current app/environment** where this skill is invoked. The tab is a visible terminal attached to that tmux session; it is not an external Terminal.app/iTerm/xterm window unless the user explicitly asks.

Mental model: each tmux session is one agent. You orchestrate from outside by writing to its input and reading its pane — what a human does by switching windows, but scripted. Your context budget is finite, so relay each agent's answer, not its whole screen (the bundled helper extracts just the reply delta).

This skill is the **tmux counterpart** of `herdr-agent-comms`. Use this for plain tmux; use `herdr-agent-comms` when agents live in Herdr.

## When to Use

Launching agents in tmux, messaging an agent in another session, broadcasting to a fleet, checking fleet status, inspecting a managed session, or reading what an agent replied. Don't use for SSH/remote shells, GNU `screen`, or driving a GUI app.

## Workflow

Six phases, in order: discover/spawn a session, resolve the exact target, send the message, wait for the reply to settle, capture it, then continue or tear down.

**Jump straight to the phase for your task** — don't read the rest:

| Your task | Start at |
|---|---|
| Spawn a new agent session | Phase 1 |
| Message an agent that's already running | Phase 2 |
| Just read a running agent's pane (no send) | Phase 5 |
| Show fleet status | Phase 5 ("Status and Inspect") |
| Inspect one agent and get an attach command | Phase 5 ("Status and Inspect") |
| Broadcast the same message to a fleet | Phase 6 ("Broadcast to a fleet") |
| Shut an agent down | Phase 6 ("Tear down") |

## Prerequisites

- **tmux installed**: `command -v tmux` must succeed. If missing, tell the user to install it (`brew install tmux` / `apt install tmux`) and stop.
- **You operate sessions you can't see.** Always confirm a session exists and inspect its pane before assuming a message landed.

## Critical Rules

1. **Confirm before destructive/irreversible actions.** Killing a session or sending `exit`/`/quit` can lose that agent's work — never without explicit user go-ahead. Reading a pane is always safe; writing is not.
2. **Verify the target before sending.** Resolve the exact session with `has-session` first (Phase 2) — a typo sends keystrokes nowhere or to the wrong agent.
3. **Wait for the agent, don't race it.** Sending a follow-up while it's still working corrupts input. Preflight before every send (Phase 3); wait until the pane settles (Phase 4) before reading or sending again.
4. **Escape what you send.** `send-keys` and the shell both interpret special characters. Follow the escaping rules in Phase 3 or messages get mangled — or worse, execute.
5. **New sessions open visibly by default.** Spawn new agent sessions in a fresh terminal tab provided by the current app/environment, attached to the tmux session. If the environment cannot open an app terminal tab, create the session detached and print the exact attach command for the user; never run `attach-session` yourself from a non-TTY shell.
6. **Default startup is autonomous and non-blocking.** Opening a visible app tab is for human observation; the orchestrator still continues with readiness checks and scripted messaging. Don't wait at startup for a human unless the user explicitly asks for interactive mode.
7. **Blocked agents need humans.** Exit code 3 / block chrome means a trust/auth/permission dialog — surface it; don't type the next task into the dialog. Re-run preflight before any recovery Enter.

## Resolve scripts/

`$0` is unreliable when snippets run inline. Probe known install locations; **repo-local copies win** over global installs:

```bash
here=""
for cand in \
  "skills/tmux-agent-comms/scripts" \
  ".agents/skills/tmux-agent-comms/scripts" \
  ".claude/skills/tmux-agent-comms/scripts" \
  "$HOME/.claude/skills/tmux-agent-comms/scripts" \
  "$HOME/.agents/skills/tmux-agent-comms/scripts"; do
  if [ -f "$cand/wait_for_idle.py" ]; then here="$cand"; break; fi
done
[ -n "$here" ] || { echo "Error: wait_for_idle.py not found in any known install location" >&2; exit 1; }
```

Reuse `$here` for `preflight_send.py`, `broadcast.sh`, and the waiter.

## Phase 1: Create or Discover Sessions

```bash
tmux list-sessions 2>/dev/null || echo "no tmux server running yet"
```

Match the target against this list (Phase 2). New sessions use the predictable pattern **`<folder>-<short-task-name>`**: folder is the current project/workspace folder, and short task is a concise slug like `reviewer`, `tests`, or `docs`. This keeps `status`, `inspect`, and attach commands grep-friendly.

To spawn, resolve a free name first because `tmux new-session` **fails if the name is taken** (exit 1):

```bash
slug() { printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-|-$//g'; }
folder="$(slug "$(basename "$PWD")")"
task="$(slug "${short_task_name:-reviewer}")"
name="${folder}-${task}"
project_dir="$PWD"
agent_cmd="${TAC_AGENT_CMD:-claude}"
tmux has-session -t "$name" 2>/dev/null && name="${name}-$(date +%s)"   # avoid collision
```

### Build `agent_cmd` (common CLIs)

| Agent | Executable | Model / thinking / skill knobs |
|---|---|---|
| **Claude Code** | `claude` | model via settings/`--model` if available; skills via project/plugin — don't invent flags |
| **pi** | `pi` | `--model <provider/id>`, `--thinking <off\|…\|max>`, `--skill <path>` (repeatable) |
| **Codex** | `codex` | interactive default; verify flags with `codex --help` |
| **OpenCode** | `opencode` | verify with `opencode --help` |
| **Gemini CLI** | `gemini` | verify with `gemini --help` |

Launch the **interactive** TUI unless the user asked for fire-and-exit. Prefer boot first, then Phase 3 the long task — do **not** dump the whole prompt as argv on first launch by default.

**Default: open a new app terminal tab.** Use the terminal-tab facility of the current app/environment where the skill is running (IDE terminal tab, coding-agent terminal tab, or equivalent). The new tab's command should create/attach the tmux session and launch the agent there:

```bash
# $agent_cmd is intentionally unquoted so multi-word TAC_AGENT_CMD values
# (e.g. claude --permission-mode bypassPermissions) expand to separate argv.
cd "$project_dir" && exec tmux new-session -s "$name" -c "$project_dir" -- $agent_cmd
```

The tab itself is the live terminal for that session. Do **not** open an external OS terminal app unless the user explicitly requests it, and do not confuse this with creating a tmux window/tab inside an existing session.

**Detached fallback** — create the session detached, then branch on *why* you fell back:

```bash
tmux new-session -d -s "$name" -c "$project_dir"
# send-keys types the command line, so multi-word TAC_AGENT_CMD is fine as one string.
tmux send-keys -t "$name" "$agent_cmd" Enter
```

- **No app-tab facility** (environment cannot open an integrated terminal tab): also print the exact command for the user to open a tab themselves:
  ```bash
  printf 'Open a new terminal tab in this app and run: cd %q && tmux attach-session -t %q\n' "$project_dir" "$name"
  ```
- **Explicit background/detached request** (user asked for a background fleet / no visible tabs): stop after the detached spawn — do **not** print an open-tab/attach instruction.

**Startup mode:** autonomous/non-blocking is the default. Use `TAC_STARTUP_MODE=autonomous|interactive` as the global default when present; a per-launch user request like `--interactive` or "show me the setup first" overrides it. In autonomous mode, open the visible app tab when available (or the matching detached fallback above), then immediately continue to readiness checks — never park the orchestrator on an interactive startup question. In interactive mode, ensure the session is visible and stop before scripted sends.

**"Spawned" ≠ "ready"** — a fresh agent often boots through a trust/auth prompt. Don't send blind. Use `--ready` so an already-idle boot counts as success (post-send waits deliberately do **not**):

```bash
# Resolve $here first (see "Resolve scripts/").
python3 "$here/wait_for_idle.py" "$name" --ready --timeout 60 --no-print; echo "ready=$?"
# exit 0 ready · 3 blocked (surface dialog) · 2 timeout · 1 error
```

For a **fleet**, spawn every session first, then run a **concurrent readiness pass** — do **not** assign work unless every agent is ready:

```bash
ready_failed=0; rpids=()
for s in myrepo-reviewer myrepo-tests myrepo-docs; do
  python3 "$here/wait_for_idle.py" "$s" --ready --timeout 60 --no-print &
  rpids+=("$!:$s")
done
for e in "${rpids[@]}"; do
  jp="${e%%:*}"; sess="${e#*:}"
  wait "$jp" || { rc=$?; ready_failed=1; echo "$sess: not ready (rc $rc)" >&2; }
done
[ "$ready_failed" -eq 0 ] || { echo "Fleet not ready; not assigning work." >&2; exit 1; }
```

The visible-tab default applies to each newly spawned session unless the user asks for a detached/background fleet.

**Showing an existing agent's terminal** (human-only): if a session already exists without a visible tab, the human can run `tmux attach-session -t "$name"` or `tmux switch-client -t "$name"` from an interactive terminal. The agent invoking either itself will fail (no TTY / no attached client). Detach with `Ctrl-b d` to return control without killing the session. See `references/tmux-recipes.md` ("Showing an agent's live terminal").

## Phase 2: Resolve the Exact Target

```bash
tmux has-session -t agent1 2>/dev/null && echo "OK: agent1 exists" || echo "MISSING: agent1"
```

If missing, run `tmux list-sessions` and pick the closest match — surface any substitution to the user rather than guessing. To target a specific window/pane, use `session:window.pane` (e.g. `-t agent1:0.1`); a bare session name targets the active pane, which is enough for single-pane agents.

## Phase 3: Send a Message

Capture the transcript **before sending**. This lets Phase 4 recognize a fast reply even if the agent finishes before the waiter starts. Split the completion marker so prompt echo cannot satisfy the wait:

```bash
# Resolve $here if not already set (see "Resolve scripts/").
if [ -z "${here:-}" ]; then
  for cand in "skills/tmux-agent-comms/scripts" ".agents/skills/tmux-agent-comms/scripts" \
    ".claude/skills/tmux-agent-comms/scripts" "$HOME/.claude/skills/tmux-agent-comms/scripts" \
    "$HOME/.agents/skills/tmux-agent-comms/scripts"; do
    [ -f "$cand/preflight_send.py" ] && { here="$cand"; break; }
  done
fi
[ -n "${here:-}" ] || { echo "Error: preflight_send.py not found" >&2; exit 1; }

target=agent1
baseline_file="$(mktemp)"
tmux capture-pane -t "$target" -p -S -80 >"$baseline_file" \
  || { echo "Error: could not capture baseline for $target" >&2; exit 1; }
marker_suffix="$(date +%s)_$$_$RANDOM"
completion_marker="TAC_DONE_$marker_suffix"
# Keep the full marker out of the prompt so prompt echo cannot satisfy the wait.
task="summarize the changes in src/

After fully finishing, concatenate and print these two parts without spaces: TAC_DONE_ and $marker_suffix"

# FAIL-CLOSED preflight IMMEDIATELY before dispatch — refuse working (rc 2),
# blocked (rc 3), or unverifiable (rc 4). Only idle (rc 0) is safe.
python3 "$here/preflight_send.py" "$target" >/dev/null \
  || { echo "Error: $target is not safe to send to (preflight failed) — see stderr" >&2; rm -f "$baseline_file"; exit 1; }

tmux send-keys -t "$target" "$task"
tmux send-keys -t "$target" Enter
```

**Escaping:** wrap the message in double quotes; a raw `;` is read by tmux as a command separator, and `$`/backticks/`"` are still expanded by the shell inside double quotes — escape them or use single quotes when the message has none of its own. For newlines or code, write to a file and load it instead of fighting escaping — see `references/tmux-recipes.md` ("Sending multi-line or code-heavy messages"). Prefer paste-buffer for multi-line bodies, then still append the split completion-marker instruction and Enter.

**Separate-Enter gotcha:** some TUIs don't submit when `Enter` rides the same call. Always send `Enter` alone after the text (as above).

**Verify delivery before you wait.** On-screen text proves it was *typed*, not submitted. The reliable signal is **post-send activity** vs the pre-send baseline (spinner chrome **or** file-to-file transcript change). One bounded check — never a poll loop:

```bash
sleep 5
after_file="$(mktemp)"
tmux capture-pane -t "$target" -p -S -80 >"$after_file" \
  || { echo "Error: post-send capture failed" >&2; rm -f "$after_file"; exit 1; }
if grep -Eq 'esc to interrupt|[⠁-⣿]' "$after_file" || ! cmp -s "$baseline_file" "$after_file"; then
  echo delivered
else
  echo NOT-DELIVERED
fi
rm -f "$after_file"
```

`delivered` / transcript activity → proceed to Phase 4. `NOT-DELIVERED` → **re-run preflight first**, then a lone Enter; never send Enter blind into a dialog the send may have triggered:

```bash
python3 "$here/preflight_send.py" "$target" >/dev/null \
  || { echo "Error: $target not safe for recovery Enter — see stderr" >&2; exit 1; }
tmux send-keys -t "$target" Enter || { echo "Error: recovery Enter failed" >&2; exit 1; }
sleep 5
after_file="$(mktemp)"
tmux capture-pane -t "$target" -p -S -80 >"$after_file"
if grep -Eq 'esc to interrupt|[⠁-⣿]' "$after_file" || ! cmp -s "$baseline_file" "$after_file"; then
  echo delivered
else
  echo "Error: $target NOT-DELIVERED — still idle after recovery Enter; re-send the task." >&2
  rm -f "$after_file"
  exit 1
fi
rm -f "$after_file"
```

Full rationale: `references/delivery-and-waiting.md`.

## Phase 4: Wait for the Reply, Then Read It

A fixed `sleep` wastes time or reads a half-written reply. Prefer the helper with the Phase 3 pre-send baseline + completion marker; without them, a fast agent can finish before the waiter snapshots the pane and leave the root waiting until timeout, and prompt echo can look complete:

```bash
[ -n "${here:-}" ] || { echo "Error: wait_for_idle.py not found — resolve \$here first" >&2; exit 1; }
python3 "$here/wait_for_idle.py" "$target" --timeout 180 --scrollback 80 \
  --baseline-file "$baseline_file" --completion-marker "$completion_marker"
rc=$?; rm -f "$baseline_file"   # capture rc BEFORE cleanup
# rc: 0 settled, 1 error, 2 timeout, 3 blocked. Propagate non-zero — not a reply.
[ "$rc" -eq 0 ] || { echo "Error: wait for $target did not complete (rc $rc)" >&2; exit "$rc"; }
```

Branch on the exit code: **0 idle** (settled, relay the printed delta), **3 blocked** (parked on a prompt needing a human — don't send, surface it, Rule 7), **2 timeout** (never settled within `--timeout`; bounds one wait, not a loop). For chrome that differs from the defaults, tune `--busy-marker`/`--block-marker` (or `TAC_BUSY_MARKERS`/`TAC_BLOCK_MARKERS`) — run `--help` for the rest.

**The verdict is advisory.** Before relaying a result the user will act on, or on any timeout, do an independent read: capture the pane, `sleep 3`, capture again. Captures differ, or either shows `esc to interrupt`/a spinner glyph → still working (keep waiting, don't send). Captures are byte-identical with no spinner marker → stalled (surface it, don't silently re-wait).

**Anti-deadloop:** set a hard overall budget (e.g. 2–3 re-waits or a wall-clock cap) before you start; when it's spent, stop and escalate — never poll indefinitely. No Python? Fall back to capture / `sleep 3` / capture / compare under the same budget. Full details: `references/delivery-and-waiting.md`.

## Phase 5: Read More (capped-tail capture)

When you need to read the pane yourself beyond the helper's delta, default to a capped tail (a fixed line-count window — distinct from Phase 3's one-shot delivery check, which is "bounded" in the no-poll-loop sense), not the bare pane or unbounded scrollback:

```bash
tmux capture-pane -t agent1 -p -S -40       # ~40 scrollback lines + visible pane
```

If the capture starts mid-sentence, the reply exceeded the window — widen stepwise (`-S -80`, ...). Only fall back to unbounded `-S -` when even a wide tail truncates — see `references/tmux-recipes.md` ("Reading scrollback robustly").

### Status and Inspect (read-only)

Use **status** when the user asks what every managed tmux agent is doing. Read only — do not send keys. Prefer sessions following the `<folder>-<short-task-name>` convention, plus any sessions launched earlier in this run. Output a table with at least: agent ID, session name, state (`in-progress` / `done` / `blocked` / `unknown`), task/progress summary, started time, and working directory.

Useful raw data:

```bash
tmux list-sessions -F '#{session_name}|#{t:session_created}'
tmux list-panes -a -F '#{session_name}|#{pane_current_path}|#{pane_current_command}'
tmux capture-pane -t "$session" -p -S -40
```

Keep status checks fast and read-only: prefer two short bounded captures (`sleep 1-3`) to detect changing output, or call `wait_for_idle.py --timeout 3 --quiet-cycles 1 --no-print` rather than the full reply-wait cycle. Classify `in-progress` when the tail changes or shows a spinner / `esc to interrupt`; `blocked` when the short waiter exits 3 or a prompt is visible; `done` when the pane is quiet and a completed reply/prompt is visible; otherwise `unknown`. Keep progress summaries short — the current task or last meaningful line, not full scrollback.

Use **inspect `<agent-id>`** for one agent. Resolve the ID to the exact session, show the same fields as status plus a bounded tail and pane details, and print the human-only attach command:

```bash
tmux attach-session -t "$session"
```

The orchestrator must not run that attach command itself (no TTY); it only gives the user a copy-paste command for their own terminal.

## Phase 6: Continue, Broadcast, or Tear Down

**Continue (steer):** a follow-up is a **brand-new send — re-run the entire Phase 3→4→5 workflow for it**, not a bare `send-keys`. Every follow-up needs its own **fresh `$baseline_file`** (Phase 4 deleted the previous one) and **fresh `$completion_marker`** (the prior joined marker is already in the transcript and would falsely satisfy this wait), plus the Phase 3 preflight immediately before dispatch and the Phase 4 wait afterward. Reusing the deleted baseline or stale marker makes the follow-up's completion unprovable. Wait for idle before sending again, and keep the overall budget across rounds — if the loop keeps re-waiting without progress, escalate rather than poll forever.

**Broadcast to a fleet:** send to every *safe* session first, then wait concurrently — never serialize a full send→wait→read per agent. Prefer the script (preflight + baselines + markers + partial-failure reporting):

```bash
"$here/broadcast.sh" "pull latest main and report status" myrepo-reviewer myrepo-tests myrepo-docs
```

**Long-running fleet status:** during multi-agent work that runs for several minutes, emit a fleet status report about every 5 minutes until all agents are done or blocked. Use the read-only Status table from Phase 5: per-agent state, current task/progress, started time, and working directory. This is a monitor/wake cadence only — never interrupt a working pane, never send keys as part of the report, and keep the same wait/budget rules from Phase 4.

**Tear down (confirmation required):**

```bash
tmux kill-session -t agent1     # one session
tmux kill-server                # everything — prefer killing named sessions individually
```

Both destroy unsaved agent state — confirm with the user first (Rule 1).

## Example

Message a running agent and relay its answer — full baseline → preflight → send → delivery check → wait with marker:

```bash
here=""
for cand in "skills/tmux-agent-comms/scripts" ".agents/skills/tmux-agent-comms/scripts" \
  ".claude/skills/tmux-agent-comms/scripts" "$HOME/.claude/skills/tmux-agent-comms/scripts" \
  "$HOME/.agents/skills/tmux-agent-comms/scripts"; do
  [ -f "$cand/wait_for_idle.py" ] && { here="$cand"; break; }
done
[ -n "$here" ] || { echo "Error: scripts not found" >&2; exit 1; }

target=reviewer
tmux has-session -t "$target" 2>/dev/null || { echo "no session '$target'"; exit 1; }

baseline_file="$(mktemp)"
tmux capture-pane -t "$target" -p -S -80 >"$baseline_file"
suffix="$(date +%s)_$$_$RANDOM"
completion_marker="TAC_DONE_$suffix"
task="summarize the open PRs

After fully finishing, concatenate and print these two parts without spaces: TAC_DONE_ and $suffix"

python3 "$here/preflight_send.py" "$target" >/dev/null \
  || { echo "not safe to send"; rm -f "$baseline_file"; exit 1; }
tmux send-keys -t "$target" "$task"
tmux send-keys -t "$target" Enter

sleep 5
after_file="$(mktemp)"
tmux capture-pane -t "$target" -p -S -80 >"$after_file"
if grep -Eq 'esc to interrupt|[⠁-⣿]' "$after_file" || ! cmp -s "$baseline_file" "$after_file"; then
  echo "delivered"
else
  python3 "$here/preflight_send.py" "$target" >/dev/null || exit 1
  tmux send-keys -t "$target" Enter
  sleep 5
fi
rm -f "$after_file"

python3 "$here/wait_for_idle.py" "$target" --timeout 180 --scrollback 80 \
  --baseline-file "$baseline_file" --completion-marker "$completion_marker"
rc=$?; rm -f "$baseline_file"
echo "wait exit=$rc"   # 0 idle · 3 blocked · 2 timeout
tmux capture-pane -t "$target" -p -S -40
```

Relay the answer to the user. If the read starts mid-sentence, widen to `-S -80` (Phase 5). On `exit=3`, don't send — show the dialog and ask how to respond. If the wait never settles within budget, stop and surface the stall (Phase 4).

## Edge Cases

- **Trust/auth dialog** — `wait_for_idle.py` / preflight return exit 3. Never send a message (would be read as menu input); surface the dialog.
- **Reply ends in a numbered list** ("1. yes 2. no") — not mistaken for a prompt; block detection uses only verified dialog strings.
- **Duplicate session name** — `tmux new-session` exits 1; resolve a free name first (Phase 1).
- **Interactive startup would hang the run** — default to autonomous startup and continue readiness checks; only enter interactive mode when the user explicitly opts in.
- **Status cannot identify an agent** — list it as `unknown` rather than guessing; `inspect` must resolve the exact session before printing an attach command.
- **Reply text contains "running"/"loading"** — busy detection scans only spinner chrome, never reply prose.
- **Message never landed** — Phase 3's post-send activity check (baseline `cmp` or spinner) catches this; preflight then lone `Enter`, re-check, re-type if still nothing.
- **Fast agent finishes before waiter starts** — use `--baseline-file` from Phase 3; without it the waiter's own snapshot can miss the reply delta.
- **Prompt echo looks like completion** — use a split `TAC_DONE_` marker; only the finished reply joins the halves.
- **Follow-up reuses old baseline/marker** — always mint fresh ones; the prior marker is already in the transcript.
- **Agent stalled** (unchanged pane, no spinner, no completion) — distinct from "still working" or a dropped delivery; surface it, don't silently re-wait.
- **Re-wait/re-send loop won't terminate** — enforce the overall budget (Phase 4); escalate rather than poll indefinitely.
- **Capped-tail capture starts mid-sentence** — reply is longer than ~40 lines; widen stepwise, only reach for unbounded `-S -` if a wide tail still truncates.
- **Returning to orchestrator control after attaching** — if the human attached manually, detach with `Ctrl-b d`; never `kill-session` just to "get back." A visible app tab can stay open while the orchestrator continues scripted send/wait/capture.
- **Need Herdr instead** — use `herdr-agent-comms` (grid in one tab, agent-status waits). This skill is tmux-only.

## Reference

- `references/delivery-and-waiting.md` — full rationale behind preflight, delivery verification (Phase 3), and waiting (Phase 4).
- `references/tmux-recipes.md` — broadcasting, concurrent readiness, multi-line sends, status/inspect, live terminal, scrollback, troubleshooting.
- `scripts/preflight_send.py` — fail-closed busy/blocked/unverifiable check before every send or recovery Enter.
- `scripts/wait_for_idle.py` — settle wait with `--baseline-file`, `--completion-marker`, `--ready`.
- `scripts/broadcast.sh` — fleet send with preflight, baselines, markers, concurrent waits.

## Step Completion Report

After a messaging or lifecycle operation, emit:

```
◆ Tmux Agent Comms ([what you did])
··································································
  Target resolved:     √ pass (session: agent1)
  Preflight:           √ pass (idle)
  Baseline captured:   √ pass
  Message sent:        √ pass
  Message delivered:   √ pass (activity vs baseline / spinner)
  Completion marker:   √ pass (joined in reply)
  Reply settled:       √ pass (quiet cycles · verdict advisory)
  Reply verified:      √ pass (manual capped-tail read)
  Reply captured:      √ pass (-S -40, not truncated)
  Fleet status:        √ pass (if long-running fleet work: ~5 min cadence; otherwise — n/a)
  Destructive action:  — none (or: confirmed by user)
  ____________________________
  Result:              PASS
```

Adapt rows to the operation — a spawn reports `Session created · Ready gate N/N`; a teardown reports `Confirmed` and `Session killed`. Use `⚠` for a dropped delivery (`Message delivered: ⚠ not delivered — re-sent`) or an escalated stall (`Reply settled: ⚠ stalled — budget spent, surfaced`).
