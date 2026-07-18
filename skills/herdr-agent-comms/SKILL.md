---
name: herdr-agent-comms
description: "Manage AI agent fleets in Herdr: split sub-agents from the root agent pane into one tab, message/wait/read via herdr CLI, steer any pane. Use for Herdr multi-agent fleets. Don't use for tmux, screen, or non-Herdr terminals."
license: MIT
effort: medium
metadata:
  version: 1.2.0
  author: "Luong NGUYEN <luongnv89@gmail.com>"
compatibility: "Requires `herdr` on PATH and a running Herdr server (`herdr status`)."
---

# Herdr Agent Comms

Manage and talk to AI agents (Claude Code, pi, Codex, OpenCode, or any CLI) by **splitting the root agent's pane**: the **root agent stays put**, each **sub-agent is a new split in the same tab**, then **send** / **wait** / **read** / **tear down** via the `herdr` CLI.

Mental model (Herdr concepts, not tmux):

| Concept | Role in this skill |
|---|---|
| **Root agent** | Orchestrator pane (usually the caller: `$HERDR_PANE_ID`) — never replaced by a sub-agent |
| **Root tab** | The root agent's tab — **single view** holding root + every sub-agent pane |
| **Sub-agent pane** | Created only by splitting the root pane (or another pane in the root tab) |
| **Agent name** | Stable handle for send/wait/read (`reviewer`, `tests`, …) |

Default layout after spawning two sub-agents:

```
Tab (root's tab)
├── pane root     ← root / orchestrator agent (you)
├── pane right    ← sub-agent reviewer
└── pane down     ← sub-agent tests
```

You orchestrate with the `herdr` CLI. Prefer agent-status waits over scrollback polling. Relay each agent's answer, not its whole screen.

This skill is the **Herdr counterpart** of `tmux-agent-comms`. Use this when agents should live in Herdr; use `tmux-agent-comms` for plain tmux.

## When to Use

Spinning up sub-agents beside the root agent in **one tab**, messaging or steering any pane, broadcasting to a fleet, or reading replies. Don't use for tmux/screen sessions or GUI apps.

## Workflow

Six phases, in order: ensure server + resolve root, split sub-agents from root, resolve targets, send, wait + read, continue or tear down.

**Jump straight to the phase for your task** — don't read the rest:

| Your task | Start at |
|---|---|
| Spin up N sub-agents beside the root agent | Phase 1 → Phase 2 |
| Message an agent that's already running | Phase 3 |
| Just read a running agent's pane (no send) | Phase 5 |
| Broadcast the same message to a fleet | Phase 6 ("Broadcast") |
| Shut sub-agents down (keep root) | Phase 6 ("Tear down") |

## Prerequisites

1. **`herdr` installed**: `command -v herdr` must succeed. If missing, install (`curl -fsSL https://herdr.dev/install.sh | sh` or `brew install herdr`) and stop.
2. **Server reachable**: `herdr status` must show a running server. If not, tell the user to attach once with `herdr` from a real terminal (do **not** run bare `herdr` from a non-TTY agent shell — it tries to launch the TUI).
3. **Never nest tmux** inside a Herdr pane if you need agent detection — run agents directly in panes.
4. **Installed binary is authority** for flags: when unsure, run `herdr <group>` with no subcommand (e.g. `herdr agent`, `herdr pane`) — never bare `herdr` for discovery.

## Critical Rules

1. **Confirm before destructive actions.** Closing panes/tabs/workspaces or `herdr server stop` can lose agent work — never without explicit user go-ahead. Reading panes is always safe. **Never close the root pane** unless the user explicitly asks to kill the orchestrator.
2. **Parse IDs from JSON.** Workspace/tab/pane IDs are opaque (`w26`, `w26:t2`, `w26:p4`). Never invent them from sidebar order.
3. **Split from the root agent — one tab.** Default spawn **splits the root agent's pane** so the human sees **root + all sub-agents in a single tab**. Do **not** create a separate fleet tab and do **not** put the first sub-agent on a new tab's root pane. New tabs only when the user explicitly asks for isolation.
4. **Prefer `--no-focus` while spawning** so focus stays on the root agent. Use `herdr agent focus <name>` when the user wants to type into a sub-agent.
5. **Wait on agent status, don't race.** After send, wait for `working` then `idle`/`done` (Phase 4). Don't send a follow-up while status is `working`.
6. **`pane run` submits text + Enter.** Prefer it over separate `send-text`/`send-keys` for prompts. `agent send` is literal text only (no Enter) — use when you must type without submitting.
7. **Blocked agents need humans.** Status `blocked` means a trust/auth/permission dialog — surface it; don't type the next task into the dialog.

## Phase 1: Ensure Server and Resolve Root Agent

```bash
command -v herdr >/dev/null || { echo "herdr missing"; exit 1; }
herdr status
```

Resolve **root** (orchestrator) context — this is the pane you split:

```bash
# Preferred when this skill runs inside Herdr (HERDR_ENV=1):
root_pane="${HERDR_PANE_ID:?}"
root_tab="${HERDR_TAB_ID:?}"
ws="${HERDR_WORKSPACE_ID:?}"

# Or resolve explicitly:
# herdr pane current --current
# herdr pane get w26:p1
```

If `HERDR_ENV` is not set (orchestrating from outside Herdr):

1. `herdr workspace list` / `herdr agent list`
2. Pick the project workspace and an existing root agent pane the user named, **or** the focused pane
3. Only if there is no usable root pane: create a workspace tab for the project and treat its root pane as root — still split sub-agents from that pane afterward (do not open one tab per sub-agent)

Also resolve `project_dir` (default: cwd of the root pane from `herdr pane get`, else `pwd`).

Optional: `herdr integration install pi|claude|codex|opencode|hermes` for better status. Not required every run.

**Done when:** you have concrete `root_pane`, `root_tab`, `ws`, and the server is running. Root agent stays alive in `root_pane`.

## Phase 2: Spawn Sub-Agents by Splitting the Root Pane

Every sub-agent is a **split of the root pane** (same tab). The root agent is **not** moved, renamed into a worker, or replaced.

### 2a — Split root → launch sub-agent

```bash
project_dir=/path/to/project   # usually root pane cwd
root_pane="$HERDR_PANE_ID"     # from Phase 1
name=reviewer
agent_cmd='pi --thinking medium'
# optional skills for pi:  --skill /path/to/SKILL.md

# free name if taken
herdr agent list | grep -q "\"name\":\"$name\"" && name="${name}-$(date +%s)"

# Split the ROOT pane (not an anonymous new tab). Always --no-focus.
dir=right   # first sub-agent: right; later: alternate down / right
split_json="$(herdr pane split "$root_pane" --direction "$dir" --cwd "$project_dir" --no-focus)"
# JSON shape: result.pane.pane_id (verify once with your herdr version if needed)
sub_pane="$(printf '%s' "$split_json" | python3 -c 'import sys,json; d=json.load(sys.stdin); r=d["result"]; print((r.get("pane") or r.get("root_pane") or r)["pane_id"])')"

herdr pane rename "$sub_pane" "$name"
herdr agent rename "$sub_pane" "$name"
herdr pane run "$sub_pane" "$agent_cmd"
```

**Second / third sub-agent** — keep splitting from the **root pane** (or the last sub-pane if root is already too narrow); stay on `root_tab`:

```bash
name=tests
herdr agent list | grep -q "\"name\":\"$name\"" && name="${name}-$(date +%s)"
split_json="$(herdr pane split "$root_pane" --direction down --cwd "$project_dir" --no-focus)"
sub_pane="$(printf '%s' "$split_json" | python3 -c 'import sys,json; d=json.load(sys.stdin); r=d["result"]; print((r.get("pane") or r)["pane_id"])')"
herdr pane rename "$sub_pane" "$name"
herdr agent rename "$sub_pane" "$name"
herdr pane run "$sub_pane" 'pi --thinking low'
```

**Alternative** (same tab, less precise about which pane is split): `herdr agent start` into the root tab:

```bash
herdr agent start "$name" --cwd "$project_dir" --workspace "$ws" --tab "$root_tab" \
  --split right --no-focus -- pi --thinking medium
```

Prefer **`pane split "$root_pane"`** so the split is anchored on the root agent, not whichever pane last held focus.

**Split direction rule:** prefer `right` when the source pane is wider than tall; prefer `down` when tall/narrow. If unknown, **alternate** `right`, `down`, `right`, …. Avoid repeating one direction until panes are unusable slivers. Optional geometry: `herdr pane layout --pane "$root_pane"`.

**Forbidden by default:** `herdr tab create` per sub-agent; hijacking the root pane with the first worker's CLI; `herdr workspace create` just to host workers when a root pane already exists in the project workspace.

**Optional (user asks for isolation):** tab-per-agent — see `references/herdr-recipes.md`. Not the default.

### 2b — Build `agent_cmd` (common CLIs)

| Agent | Executable | Model / thinking / skill knobs |
|---|---|---|
| **pi** | `pi` | `--model <provider/id>`, `--thinking <off\|…\|max>`, `--skill <path>` (repeatable) |
| **Claude Code** | `claude` | model via settings/`--model` if available; skills via project/plugin — don't invent flags |
| **Codex** | `codex` | interactive default; verify flags with `codex --help` |
| **OpenCode** | `opencode` | verify with `opencode --help` |

Launch the **interactive** TUI (no `-p`/`exec` non-interactive mode) unless the user asked for fire-and-exit. Do **not** pass the long task as argv on first launch by default — boot first, then `pane run` the task.

When using `herdr agent start … -- <argv>`, put only the launcher (+ model/thinking/skill flags) after `--`, not the long task prompt.

### 2c — Ready, then assign work

```bash
# boot → idle (or blocked on trust) — per SUB-agent pane
herdr wait agent-status "$sub_pane" --status idle --timeout 60000
# if timeout: herdr pane get / herdr agent explain "$sub_pane"
# if blocked: surface to user (Rule 7)

herdr pane run "$sub_pane" "Review the open PR diff and report only actionable findings."
herdr wait agent-status "$sub_pane" --status working --timeout 30000 || true
```

**Fleet spawn:** split every sub-agent first (`--no-focus`), launch every CLI, then wait/read concurrently — don't fully serialize spawn→wait→read per agent when the user wants parallel work. `scripts/broadcast.sh` fans messages after spawn.

**Human visibility:** root + sub-agents already share one tab. No extra tab focus required if the human is already on the root tab. Optional: `herdr agent focus reviewer` to type into one sub-agent; return focus to root when done orchestrating from the TUI.

Detach the Herdr client with `prefix+q` (`ctrl+b` then `q`); agents keep running.

**Done when:** each sub-agent has `sub_pane` + agent `name`, **same `root_tab` as the root pane**, root pane still holds the orchestrator, status is not stuck on `unknown` after boot wait, and initial tasks (if any) have been submitted.

## Phase 3: Resolve the Exact Target

Prefer the **agent name** when unique; fall back to `pane_id`:

```bash
herdr agent list
herdr agent get reviewer          # or: herdr pane get w26:p4
```

If the name is missing, list agents and surface the closest match — don't silently retarget. Record both `name` and `pane_id` for later steps (`wait agent-status` wants a pane id; `agent send`/`agent wait` accept names).

**Done when:** one concrete target id is chosen and exists in `agent list` / `pane get`.

## Phase 4: Send a Message

```bash
# preferred — text + Enter
herdr pane run "$pane_id" "summarize the changes in src/"

# by name (literal text only — add Enter yourself if needed)
herdr agent send reviewer "summarize the changes in src/"
herdr pane send-keys "$pane_id" enter
```

**Escaping:** pass the message as a single argv to `herdr` (quoted for the shell). For multi-line or code-heavy payloads, write a temp file and send a short instruction that reads it — see `references/herdr-recipes.md`.

**Verify delivery:** after send, status should leave `idle` for `working` (or stay `blocked` if a dialog ate the input):

```bash
herdr wait agent-status "$pane_id" --status working --timeout 15000 \
  && echo delivered || echo NOT-DELIVERED
```

`NOT-DELIVERED` → lone Enter via `herdr pane send-keys "$pane_id" enter`, re-check; if still idle with no new output, re-send. Inspect with `herdr pane read "$pane_id" --source recent-unwrapped --lines 40`.

## Phase 5: Wait for the Reply, Then Read It

Use Herdr status waits (not fixed `sleep`). Completion may be **`done`** (unseen, usually background) **or `idle`** (seen / focused tab) — wait for either:

```bash
# After delivery verified (Phase 4). Poll until idle|done|blocked or budget spent.
deadline=$((SECONDS + 180))
while (( SECONDS < deadline )); do
  st=$(herdr pane get "$pane_id" | python3 -c 'import sys,json; print(json.load(sys.stdin)["result"]["pane"].get("agent_status",""))')
  case "$st" in
    done|idle) echo "settled:$st"; break ;;
    blocked) echo "blocked"; break ;;
    working) herdr wait agent-status "$pane_id" --status done --timeout 15000 \
               || herdr wait agent-status "$pane_id" --status idle --timeout 15000 || true ;;
    *) sleep 2 ;;
  esac
done
# Or: python3 scripts/wait_for_idle.py "$pane_id" --timeout 180
```

Treat **either `idle` or `done` as completed** — difference is only whether the result was seen. Never wait only on `done` for the full budget: a focused-tab finish stays `idle` and will time out.

Then read a capped recent transcript:

```bash
herdr pane read "$pane_id" --source recent-unwrapped --lines 80
# or: herdr agent read reviewer --source recent-unwrapped --lines 80
```

Sources: `visible` (viewport), `recent` (rendered scrollback), `recent-unwrapped` (preferred for transcripts), `detection` (bottom buffer for debug).

**Branch on outcomes:**

| Signal | Action |
|---|---|
| status `done`/`idle` after work | Relay the read output |
| status `blocked` | Surface dialog; don't send more |
| wait timeout | `pane get` + `pane read` + `agent explain`; escalate — don't poll forever |
| status still `working` | Keep waiting under a hard overall budget (e.g. 2–3 re-waits) |

Optional helper when status stays `unknown` (no integration / undetected CLI): `python3 scripts/wait_for_idle.py <pane_id>` polls `pane read` for content stability — see script `--help`.

**Done when:** you either relay a reply delta or report blocked/timeout with evidence.

## Phase 6: Continue, Broadcast, or Tear Down

**Continue (steer):** focus if the human wants the live TUI, or keep messaging from the CLI:

```bash
herdr agent focus reviewer          # jump UI to that agent
herdr pane run "$pane_id" "Also check the failing test."
# then Phase 5 again
```

**Broadcast to a fleet:** send to every target first, then wait concurrently:

```bash
scripts/broadcast.sh "pull latest main and report status" reviewer tests docs
# or pane ids: scripts/broadcast.sh "..." w26:p4 w26:p6
```

**Fleet status (read-only):**

```bash
herdr agent list
herdr workspace list
```

**Tear down (confirmation required):**

```bash
herdr pane close "$sub_pane"        # one sub-agent — preferred
# close every sub-agent pane this skill created; leave root_pane alone
# herdr tab close "$root_tab"      # only if user wants the whole tab gone (kills root too)
# herdr workspace close "$ws"      # whole project workspace — confirm
# herdr server stop                 # kills everything — last resort, confirm
```

Never `server stop` from inside an active session unless the user explicitly wants the server and all panes dead. Never close `root_pane` when only tearing down workers.

## Example

From the root agent (inside Herdr), split two sub-agents into the same tab and collect answers:

```bash
# Phase 1 — root is the caller
root_pane="$HERDR_PANE_ID"
root_tab="$HERDR_TAB_ID"
ws="$HERDR_WORKSPACE_ID"
project_dir="$(pwd)"

spawn_sub() {
  local name="$1" dir="$2" cmd="$3" task="$4"
  local split_json pane
  herdr agent list | grep -q "\"name\":\"$name\"" && name="${name}-$(date +%s)"
  split_json="$(herdr pane split "$root_pane" --direction "$dir" --cwd "$project_dir" --no-focus)"
  pane="$(printf '%s' "$split_json" | python3 -c 'import sys,json; d=json.load(sys.stdin); r=d["result"]; print((r.get("pane") or r)["pane_id"])')"
  herdr pane rename "$pane" "$name"
  herdr agent rename "$pane" "$name"
  herdr pane run "$pane" "$cmd"
  herdr wait agent-status "$pane" --status idle --timeout 60000
  herdr pane run "$pane" "$task"
  printf '%s\n' "$pane"
}

p1="$(spawn_sub reviewer right 'pi --thinking medium' 'Review recent commits for risk; bullet findings only.')"
p2="$(spawn_sub tests down 'pi --thinking low' 'Outline a minimal test plan for the last change.')"

# Same tab: root_pane + p1 + p2
python3 scripts/wait_for_idle.py "$p1" --timeout 180
herdr pane read "$p1" --source recent-unwrapped --lines 80
# optional: herdr agent focus reviewer
```

## Edge Cases

- **Not inside Herdr / no server** — CLI still talks to the socket if the server runs; if `herdr status` fails, user must start `herdr` once in a real terminal. Outside Herdr, resolve an existing root pane before splitting.
- **Nested `herdr` launch** — if `HERDR_ENV=1`, never run bare `herdr` (blocked by design). Use CLI subcommands only.
- **Trust/auth dialog** — status `blocked`; surface it, don't submit the task.
- **`idle` vs `done`** — both mean "finished or waiting for input"; `done` = unseen completion in background. Accept either after work.
- **Name collision** — `agent rename` / `agent start` names must be unique; suffix with epoch if taken.
- **Wrong workspace** — never spawn project B agents into project A's workspace; re-resolve Phase 1.
- **Status `unknown`** — install integration or use `scripts/wait_for_idle.py` + `pane read`.
- **Too many splits** — more than ~4 panes in one tab gets cramped; still split from root unless the user asks for tab-per-agent.
- **User wants to steer** — `herdr agent focus <name>` for a sub-agent; keep CLI follow-ups only when not fighting their keyboard.
- **Closing the wrong pane** — only close **sub-agent** panes this skill created; never close root unless asked.
- **Accidental new fleet tab** — if you created a tab by mistake, move work into root's tab via splits from `root_pane` and close the empty tab only with confirmation.

## Reference

- `references/herdr-recipes.md` — fleet layouts, multi-line sends, focus/steer, scrollback, troubleshooting.
- `references/delivery-and-waiting.md` — delivery checks, idle/done/blocked, budgets.
- Official concepts: https://herdr.dev/docs/concepts/ · CLI: https://herdr.dev/docs/cli-reference/ · cheatsheet: https://luongnv.com/awesome-cheatsheets/cheatsheets/herdr/

## Step Completion Report

After a messaging or lifecycle operation, emit:

```
◆ Herdr Agent Comms ([what you did])
··································································
  Server:              √ pass (herdr status)
  Workspace:           √ pass (w26 · project label)
  Root resolved:       √ pass (pane: w26:p1 · tab: w26:t1)
  Target resolved:     √ pass (name: reviewer · pane: w26:p4 · same tab as root)
  Message sent:        √ pass (pane run)
  Message delivered:   √ pass (status → working)
  Reply settled:       √ pass (status done|idle)
  Reply captured:      √ pass (recent-unwrapped, not truncated)
  Destructive action:  — none (or: confirmed by user; root kept)
  ____________________________
  Result:              PASS
```

Adapt rows to the operation — a spawn reports `Root kept · N sub-panes split`; a teardown reports `Confirmed` and `Sub-panes closed (root kept)`. Use `⚠` for dropped delivery or escalated stall.
