---
name: herdr-agent-comms
description: "Manage AI agent fleets in Herdr: split root + sub-agents into one tab as a tiled grid, message/wait/read via herdr CLI, steer any pane. Use for Herdr multi-agent fleets. Don't use for tmux, screen, or non-Herdr terminals."
license: MIT
effort: medium
metadata:
  version: 1.9.0
  author: "Luong NGUYEN <luongnv89@gmail.com>"
compatibility: "Requires `herdr` on PATH and a running Herdr server (`herdr status`)."
---

# Herdr Agent Comms

Manage and talk to AI agents (Claude Code, pi, Codex, OpenCode, or any CLI) by building a **grid layout in the root agent's tab**: the **root agent stays put**, each **sub-agent is a new tiled split**, then **send** / **wait** / **read** / **tear down** via the `herdr` CLI.

Mental model (Herdr concepts, not tmux):

| Concept | Role in this skill |
|---|---|
| **Root agent** | Orchestrator pane (usually the caller: `$HERDR_PANE_ID`) — never replaced by a sub-agent |
| **Root tab** | The root agent's tab — **single row of equal-width columns** holding root + every sub-agent pane |
| **Sub-agent pane** | Created by splitting the rightmost column `right`, then resizing every column (including root) down to the new equal share |
| **Agent name** | Stable handle for send/wait/read (`reviewer`, `tests`, …) |

Default layout after spawning three sub-agents (**equal-width columns, root included**):

```
Tab (root's tab)
┌──────────┬──────────┬──────────┬──────────┐
│ root(you)│ reviewer │ tests    │ docs     │
└──────────┴──────────┴──────────┴──────────┘
```
(All columns — root and every sub-agent — end up the same width, ±1 terminal
cell. Adding a column means splitting the current rightmost pane `right`
(`--ratio 1/N`, so the new right pane lands on the `1/N` equal target), then
running an iterative equalizer that re-converges every column to `1/N`.
`next_grid_split.py` does both (`--equalize`); see Phase 2a and "Equal-width
columns" below for the verified `herdr` semantics.)

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
3. **Equal-width column grid in the root tab.** Default spawn builds a **row of equal-width columns that includes the root agent**. Every split is `right` on the current rightmost column, followed by resizing every column (including root) down to the new `1/N` share — never leave root or a worker wider than the others. Do **not** create a separate fleet tab and do **not** put the first sub-agent on a new tab's root pane. New tabs only when the user explicitly asks for isolation.
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

## Phase 2: Spawn Sub-Agents into a Grid (Root Included)

Every sub-agent joins the **same tab as the root agent** as part of a **tiled grid**. The root agent is **not** moved, renamed into a worker, or replaced.

### 2a — Split the rightmost column, equalize widths → launch sub-agent

Every column — root included — must end up the **same width**. A split alone can't do this for 3+ columns (it only resizes the pane you split), so each spawn is **split the rightmost column, then run the iterative equalizer**. `next_grid_split.py` handles both steps; the `herdr` split/resize semantics it relies on are verified live against herdr 0.7.4 — see `references/herdr-recipes.md` ("Equal-width columns — verified semantics") for the details and the manual fallback.

```bash
project_dir=/path/to/project   # usually root pane cwd
root_pane="$HERDR_PANE_ID"     # from Phase 1

# Resolve scripts/ robustly: $0 is unreliable when an agent runs this inline
# (it points at the shell, not the skill), so probe known install locations
# instead. Repo-local copies win over global installs so a repo pinned at a
# commit isn't silently overridden by whatever is installed globally.
here=""
for cand in \
  "skills/herdr-agent-comms/scripts" \
  ".agents/skills/herdr-agent-comms/scripts" \
  ".claude/skills/herdr-agent-comms/scripts" \
  "$HOME/.claude/skills/herdr-agent-comms/scripts" \
  "$HOME/.agents/skills/herdr-agent-comms/scripts"; do
  if [ -f "$cand/next_grid_split.py" ]; then here="$cand"; break; fi
done
[ -n "$here" ] || { echo "Error: next_grid_split.py not found in any known install location (repo, .agents/, .claude/, \$HOME). Fix the install or set \$here manually before retrying." >&2; exit 1; }
name=reviewer
agent_cmd='pi --thinking medium'
# optional skills for pi:  --skill /path/to/SKILL.md

# free name if taken
herdr agent list | grep -q "\"name\":\"$name\"" && name="${name}-$(date +%s)"

# Plan line: "split <rightmost> right --ratio <1/N>". ratio=1/N so the new
# right pane lands on the 1/N equal target (see "Equal-width columns" below).
# Guard EVERY step — a failure anywhere must abort, not launch into a broken
# or half-built layout. (The planner also rejects 2D/stacked layouts.)
plan="$(python3 "$here/next_grid_split.py" --root-pane "$root_pane")" || { echo "Error: split planning failed (bad/unsupported layout?)." >&2; exit 1; }
read -r _ split_from _dir _ratio_flag ratio < <(head -1 <<<"$plan")
[ -n "$split_from" ] && [ -n "$ratio" ] || { echo "Error: empty split plan; refusing to split." >&2; exit 1; }
split_json="$(herdr pane split "$split_from" --direction right --ratio "$ratio" --cwd "$project_dir" --no-focus)" || { echo "Error: 'herdr pane split' failed." >&2; exit 1; }
sub_pane="$(printf '%s' "$split_json" | python3 -c 'import sys,json; d=json.load(sys.stdin); r=d["result"]; print((r.get("pane") or r.get("root_pane") or r)["pane_id"])')" || { echo "Error: could not parse new pane id." >&2; exit 1; }
[ -n "$sub_pane" ] || { echo "Error: empty new pane id." >&2; exit 1; }

# Equalize every column (a split alone leaves pre-existing columns wider than
# 1/N). HARD GATE: on failure (resize error or non-convergence) do NOT launch
# into a broken layout — abort and name the orphan. Never swallow with `|| true`.
if ! python3 "$here/next_grid_split.py" --equalize --root-pane "$root_pane"; then
  echo "Error: equalization failed; NOT launching '$name'. Orphan split pane: $sub_pane ('herdr pane close $sub_pane' to undo)." >&2
  exit 1
fi

herdr pane rename "$sub_pane" "$name" >/dev/null || { echo "Error: rename failed; orphan $sub_pane." >&2; exit 1; }
herdr agent rename "$sub_pane" "$name" >/dev/null || { echo "Error: agent rename failed; orphan $sub_pane." >&2; exit 1; }
herdr pane run "$sub_pane" "$agent_cmd" >/dev/null || { echo "Error: launch failed; orphan $sub_pane." >&2; exit 1; }
```

**Second / third sub-agent** — identical: re-run the planner, split, then `--equalize` (the target share shrinks as columns are added, and the equalizer always converges to equal-within-1-cell). Just change `name` and `agent_cmd`.

**Manual fallback** when the helper is unavailable: split the current rightmost column `right`, then equalize by hand — see `references/herdr-recipes.md` ("Equal-width columns"). Stay on `root_tab`.

**Alternative** (same tab, not equal-width without an equalize pass): `herdr agent start` into the root tab, then run `next_grid_split.py --equalize`:

```bash
herdr agent start "$name" --cwd "$project_dir" --workspace "$ws" --tab "$root_tab" \
  --split right --no-focus -- pi --thinking medium
# Same hard gate: abort if the grid can't be equalized rather than leaving it uneven.
python3 "$here/next_grid_split.py" --equalize --root-pane "$root_pane" || {
  echo "Error: equalization failed after agent start; inspect 'herdr pane layout --pane $root_pane'." >&2; exit 1; }
```

Prefer **`next_grid_split.py` split + `--equalize`** so the grid includes root and stays equal-width. This alternative skips the equalize step unless you add it.

**Grid rules:**
1. One tab only: root + every sub-agent.
2. Every split targets the current **rightmost** column.
3. Direction: always `right` — this is a single row of equal-width columns, not a 2D grid. There is no `down` case in the default layout.
4. After every split, run the equalizer — a split alone only sizes the new pane; it does not shrink the columns already in place, so 3+ columns need the equalize pass.
5. Always `--no-focus` so the root keeps the keyboard.
6. Optional check: `herdr pane layout --pane "$root_pane"` should show N rects of near-equal `rect.width` (equal within ~1 cell), not one wide pane and thin strips.

**Equal-width columns — behavior:** herdr `pane split --ratio R` sizes only the split pane (`R` = the existing/left child's fraction; the new right pane gets `1-R`). Splitting the rightmost column with `--ratio 1/N` makes the new pane `(N-1)/N` of that column = `1/N` of the whole tab (the equal target). `pane resize --amount` is a *delta* (cells as a fraction of tab width) whose freed space redistributes proportionally across neighbors — so a single split or a single resize pass cannot equalize 3+ columns. The equalizer sweeps internal boundaries left to right, growing the neighbor-bearing pane toward each target, and iterates until the spread is ≤1 cell. This was verified live against herdr 0.7.4 (2→105/105, 3→70/70/70, 4→53/53/52/52, 5→42×5). Because widths are whole terminal cells, exact equality only holds when the tab width divides evenly; otherwise columns differ by ≤1 cell. A resize failure or non-convergence is a **hard error** — `--equalize` exits non-zero and the spawn recipes abort (they do **not** launch a worker into an uneven layout). Full semantics and the derivation are in `references/herdr-recipes.md`.

**Forbidden by default:** `herdr tab create` per sub-agent; hijacking the root pane with the first worker's CLI; `herdr workspace create` just to host workers when a root pane already exists; splitting a column other than the current rightmost one.

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

# Assign through Phase 4 so a pre-send baseline is captured before pane run.
# Then collect through Phase 5 with that baseline.
```

**Fleet spawn:** split every sub-agent first (`--no-focus`), launch every CLI, then wait/read concurrently — don't fully serialize spawn→wait→read per agent when the user wants parallel work. `scripts/broadcast.sh` fans messages after spawn.

**Human visibility:** root + sub-agents already share one tab. No extra tab focus required if the human is already on the root tab. Optional: `herdr agent focus reviewer` to type into one sub-agent; return focus to root when done orchestrating from the TUI.

Detach the Herdr client with `prefix+q` (`ctrl+b` then `q`); agents keep running.

**Done when:** each sub-agent has `sub_pane` + agent `name`, **same `root_tab` as the root pane**, layout is a **row of equal-width columns that includes the root pane** (verified via `herdr pane layout` — not stacked slivers or one wide pane), root pane still holds the orchestrator, status is not stuck on `unknown` after boot wait, and initial tasks (if any) have been submitted.

## Phase 3: Resolve the Exact Target

Prefer the **agent name** when unique; fall back to `pane_id`:

```bash
herdr agent list
herdr agent get reviewer          # or: herdr pane get w26:p4
```

If the name is missing, list agents and surface the closest match — don't silently retarget. Record both `name` and `pane_id` for later steps (`wait agent-status` wants a pane id; `agent send`/`agent wait` accept names).

**Done when:** one concrete target id is chosen and exists in `agent list` / `pane get`.

## Phase 4: Send a Message

Capture the transcript **before sending**. This lets Phase 5 recognize a fast reply even if the agent finishes before the waiter starts:

```bash
baseline_file="$(mktemp)"
herdr pane read "$pane_id" --source recent-unwrapped --lines 80 >"$baseline_file"
marker_suffix="$(date +%s)_$$_$RANDOM"
completion_marker="HERDR_DONE_$marker_suffix"

# Keep the full marker out of the prompt so prompt echo cannot satisfy the wait.
task="summarize the changes in src/

After fully finishing, concatenate and print these two parts without spaces: HERDR_DONE_ and $marker_suffix"
herdr pane run "$pane_id" "$task"

# by name (literal text only — add Enter yourself if needed)
# herdr agent send reviewer "summarize the changes in src/"
# herdr pane send-keys "$pane_id" enter
```

**Escaping:** pass the message as a single argv to `herdr` (quoted for the shell). For multi-line or code-heavy payloads, write a temp file and send a short instruction that reads it — see `references/herdr-recipes.md`.

**Verify delivery:** after send, status should leave `idle` for `working` (or stay `blocked` if a dialog ate the input):

```bash
if herdr wait agent-status "$pane_id" --status working --timeout 15000; then
  echo delivered
elif ! cmp -s "$baseline_file" <(herdr pane read "$pane_id" --source recent-unwrapped --lines 80); then
  echo delivered-transcript-activity
else
  echo NOT-DELIVERED
fi
```

`NOT-DELIVERED` → lone Enter via `herdr pane send-keys "$pane_id" enter`, re-check; if still idle with no new output, re-send. A transcript change proves delivery activity, but may be only the echoed prompt; do **not** submit an extra Enter. The split completion marker lets Phase 5 distinguish echo from a finished reply.

## Phase 5: Wait for the Reply, Then Read It

Use Herdr status waits (not fixed `sleep`). Completion may be **`done`** (unseen, usually background) **or `idle`** (seen / focused tab) — wait for either. Prefer the helper with the Phase 4 pre-send baseline; without it, a fast agent can finish before the waiter snapshots the pane and leave the root waiting until timeout:

```bash
# $here is the scripts/ dir. If Phase 2 already resolved it, reuse it;
# jumping straight here (e.g. "message an agent that's already running")
# skips Phase 2, so probe install locations again rather than assume it's set.
# Repo-local copies win over global installs (see Phase 2a).
if [ -z "${here:-}" ]; then
  for cand in \
    "skills/herdr-agent-comms/scripts" \
    ".agents/skills/herdr-agent-comms/scripts" \
    ".claude/skills/herdr-agent-comms/scripts" \
    "$HOME/.claude/skills/herdr-agent-comms/scripts" \
    "$HOME/.agents/skills/herdr-agent-comms/scripts"; do
    if [ -f "$cand/wait_for_idle.py" ]; then here="$cand"; break; fi
  done
fi
[ -n "${here:-}" ] || { echo "Error: wait_for_idle.py not found in any known install location (repo, .agents/, .claude/, \$HOME). Fix the install or set \$here manually before retrying." >&2; exit 1; }
python3 "$here/wait_for_idle.py" "$pane_id" --timeout 180 --lines 80 \
  --baseline-file "$baseline_file" --completion-marker "$completion_marker"
rc=$?
rm -f "$baseline_file"
# rc: 0 settled, 2 timeout, 3 blocked
```

Manual fallback after delivery is verified:

```bash
# Poll until idle|done|blocked or budget spent.
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
# Or use the helper instead (resolve $here first — see the block above).
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

# Resolve scripts/ by probing known install locations (not $0 — unreliable
# when this snippet runs inline rather than as a saved script file).
# Repo-local copies win over global installs (see Phase 2a).
here=""
for cand in \
  "skills/herdr-agent-comms/scripts" \
  ".agents/skills/herdr-agent-comms/scripts" \
  ".claude/skills/herdr-agent-comms/scripts" \
  "$HOME/.claude/skills/herdr-agent-comms/scripts" \
  "$HOME/.agents/skills/herdr-agent-comms/scripts"; do
  if [ -f "$cand/next_grid_split.py" ]; then here="$cand"; break; fi
done
[ -n "$here" ] || { echo "Error: next_grid_split.py not found in any known install location (repo, .agents/, .claude/, \$HOME). Fix the install or set \$here manually before retrying." >&2; exit 1; }

# PASTE the canonical, fully-guarded `spawn_sub` function definition from
# references/herdr-recipes.md ("Spawn N sub-agents into an equal-width grid")
# HERE before the calls below — this example calls it but does not redefine
# it. That function guards planning, split, pane-id parse, equalize, rename,
# launch, and readiness, prints the pane id ONLY after a confirmed launch, and
# returns non-zero on any failure.

# Every caller MUST abort on non-zero — `$(...)` hides spawn_sub's exit status:
p1="$(spawn_sub reviewer 'pi --thinking medium')" || { echo "reviewer failed to place; aborting" >&2; exit 1; }
p2="$(spawn_sub tests 'pi --thinking low')" || { echo "tests failed to place; aborting" >&2; exit 1; }

# Capture before send so even instant replies are observable.
b1="$(mktemp)"; b2="$(mktemp)"
herdr pane read "$p1" --source recent-unwrapped --lines 80 >"$b1"
herdr pane read "$p2" --source recent-unwrapped --lines 80 >"$b2"
s1="$(date +%s)_$$_1_$RANDOM"; s2="$(date +%s)_$$_2_$RANDOM"
herdr pane run "$p1" "Review recent commits for risk; bullet findings only. When finished, concatenate and print: HERDR_DONE_ and $s1"
herdr pane run "$p2" "Outline a minimal test plan. When finished, concatenate and print: HERDR_DONE_ and $s2"

# Same tab: root_pane + p1 + p2
python3 "$here/wait_for_idle.py" "$p1" --timeout 180 --lines 80 --baseline-file "$b1" --completion-marker "HERDR_DONE_$s1"
python3 "$here/wait_for_idle.py" "$p2" --timeout 180 --lines 80 --baseline-file "$b2" --completion-marker "HERDR_DONE_$s2"
rm -f "$b1" "$b2"
# optional: use "$here/broadcast.sh" to baseline/send/wait concurrently
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
- **Too many splits** — more than ~4 panes in one tab gets cramped; keep the grid helper, or switch to tab-per-agent only if the user asks.
- **Unequal-width columns** — you split without the equalize pass, or split a pane other than the current rightmost column; re-run `python3 scripts/next_grid_split.py --equalize --root-pane "$root_pane"` to re-converge the grid.
- **User wants to steer** — `herdr agent focus <name>` for a sub-agent; keep CLI follow-ups only when not fighting their keyboard.
- **Closing the wrong pane** — only close **sub-agent** panes this skill created; never close root unless asked.
- **Accidental new fleet tab** — if you created a tab by mistake, move work into root's tab via grid splits and close the empty tab only with confirmation.

## Reference

- `references/herdr-recipes.md` — grid layouts, multi-line sends, focus/steer, scrollback, troubleshooting.
- `scripts/next_grid_split.py` — plan the next split (`--ratio 1/N`) and run the live iterative equalizer (`--equalize`) for an equal-width grid.
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

Adapt rows to the operation — a spawn reports `Root kept · grid N panes · N-1 sub-panes split`; a teardown reports `Confirmed` and `Sub-panes closed (root kept)`. Use `⚠` for dropped delivery or escalated stall.
