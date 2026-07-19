# Delivery and waiting (Herdr)

Rationale for Phase 4–5 of `herdr-agent-comms`. Prefer Herdr agent-status waits over scrollback polling.

## Why status beats sleep

A fixed `sleep N` either wastes time or reads a half-written reply. Herdr already classifies panes:

| Status | Meaning |
|---|---|
| `working` | Agent is busy (spinner / tools) |
| `blocked` | Needs human input (trust, auth, permissions) |
| `done` | Finished; result not yet "seen" (usually background tab) |
| `idle` | Waiting for input; result considered seen or never worked |
| `unknown` | Not detected / no integration |

`herdr wait agent-status <pane_id> --status <state> [--timeout MS]` returns when the pane **is already** in that state or **transitions** into it. Timeouts exit non-zero (typically `1`).

## Delivery verification

After `pane run` / send:

1. Expect transition toward `working` within ~15s for a real task.
2. If still `idle`/`done` with no new transcript lines → likely not submitted → lone `enter`, then re-check.
3. If `blocked` → dialog ate focus; do not treat as delivered task.

`$sd` below is the skill's `scripts/` dir (resolve it as SKILL.md Phase 4/5 do: probe repo-local then `.agents/`, `.claude/`, `$HOME`).

```bash
# $sd = the skill's scripts/ dir. FAIL-CLOSED preflight before EVERY send —
# the single-target twin of broadcast.sh Phase 1b. Refuse to type a task into a
# working (rc 2), blocked (rc 3), or unverifiable/off-enum (rc 4) pane; only
# idle/done/unknown (rc 0) is safe. Skipping this let a task be typed into a
# blocked trust dialog and still report success.
python3 "$sd/preflight_send.py" "$pane" >/dev/null \
  || { echo "Error: $pane not safe to send to (preflight failed) — see stderr" >&2; exit 1; }

baseline="$(mktemp)"
herdr pane read "$pane" --source recent-unwrapped --lines 80 >"$baseline" \
  || { echo "Error: baseline read failed for $pane" >&2; exit 1; }
suffix="$(date +%s)_$$_$RANDOM"
completion_marker="HERDR_DONE_$suffix"
task="do the thing

After fully finishing, concatenate and print these parts without spaces: HERDR_DONE_ and $suffix"
herdr pane run "$pane" "$task" || { echo "Error: send failed for $pane" >&2; exit 1; }
if herdr wait agent-status "$pane" --status working --timeout 15000; then
  echo delivered
else
  # Read post-send into a SECOND FILE and compare file-to-file. `$(...)` capture
  # strips trailing newlines the baseline file keeps, so identical transcripts
  # would falsely compare as "activity". A failed read is an error, not delivery.
  after="$(mktemp)"
  herdr pane read "$pane" --source recent-unwrapped --lines 80 >"$after" \
    || { echo "Error: post-send read failed for $pane" >&2; rm -f "$after"; exit 1; }
  if ! cmp -s "$baseline" "$after"; then
    echo delivered-transcript-activity
  else
    # Re-run the preflight before the recovery Enter: the send may have flipped
    # the pane into a `blocked` dialog, and a bare Enter would answer THAT
    # dialog, not deliver the task. Never send the Enter blind.
    python3 "$sd/preflight_send.py" "$pane" >/dev/null \
      || { echo "Error: $pane not safe for recovery Enter (blocked/working/unverifiable) — see stderr" >&2; rm -f "$after"; exit 1; }
    # Guard the keystroke, then PROPAGATE a failed re-wait. `|| echo NOT-DELIVERED`
    # alone exits 0 — a genuine non-delivery would be reported as success.
    herdr pane send-keys "$pane" enter \
      || { echo "Error: recovery Enter failed for $pane" >&2; rm -f "$after"; exit 1; }
    herdr wait agent-status "$pane" --status working --timeout 10000 \
      || { echo "Error: $pane NOT-DELIVERED — still idle after recovery Enter; re-send the task." >&2; rm -f "$after"; exit 1; }
  fi
  rm -f "$after"
fi
```

On-screen text alone does not prove submission. Status `working` or output different from the **pre-send baseline** proves delivery activity. The difference may only be prompt echo. Split the completion marker into two prompt fragments; only the finished reply contains the joined marker. Keep `baseline` and `completion_marker` for the wait.

## Completion: idle vs done

Both mean "not working anymore." After a task:

- Background tab/workspace → often **`done`**
- Active tab with focused client → often **`idle`**
- Focusing the pane turns `done` → `idle`

Orchestrator pattern — **accept either terminal state**; do not spend the whole budget on `done` alone (focused tabs finish as `idle`):

```bash
# Preferred helper. The pre-send baseline closes the fast-completion race.
# $here = scripts/ dir; probe install locations, don't derive from $0/BASH_SOURCE.
# Repo-local copies win over global installs; fail fast if none resolve:
#   for cand in "skills/herdr-agent-comms/scripts" \
#               ".agents/skills/herdr-agent-comms/scripts" \
#               ".claude/skills/herdr-agent-comms/scripts" \
#               "$HOME/.claude/skills/herdr-agent-comms/scripts" \
#               "$HOME/.agents/skills/herdr-agent-comms/scripts"; do
#     [ -f "$cand/wait_for_idle.py" ] && here="$cand" && break
#   done
#   [ -n "$here" ] || { echo "Error: wait_for_idle.py not found" >&2; exit 1; }
python3 "$here/wait_for_idle.py" "$pane" --timeout 180 --lines 80 \
  --baseline-file "$baseline" --completion-marker "$completion_marker"
rc=$?               # capture BEFORE cleanup — `rm` would clobber $?
rm -f "$baseline"
# Act on the waiter's exit and PROPAGATE it — 0 done/idle, 1 error, 2 timeout,
# 3 blocked. Any non-zero means no delivered reply; exit non-zero, don't fall
# through to the manual poll as if the wait had succeeded.
case "$rc" in
  0) : ;;
  3) echo "$pane: BLOCKED — a human must answer a dialog" >&2; exit 3 ;;
  2) echo "$pane: TIMEOUT before completion" >&2; exit 2 ;;
  *) echo "$pane: waiter failed (rc $rc)" >&2; exit "$rc" ;;
esac

# Manual alternative: poll pane get for idle|done|blocked. FAIL-CLOSED status
# read — a failed/malformed `herdr pane get` errors out rather than sleeping.
# Track the OUTCOME and propagate it: `blocked` must exit 3 and deadline
# exhaustion must exit 2. Breaking out silently (or letting the while condition
# lapse) would fall through with status 0 — reporting a blocked/timed-out wait
# as a successful completion.
deadline=$((SECONDS + 180)); settled=""
while (( SECONDS < deadline )); do
  out=$(herdr pane get "$pane" 2>/dev/null) || { echo "status lookup failed for $pane" >&2; exit 1; }
  st=$(printf '%s' "$out" | python3 -c 'import sys,json
V={"idle","working","blocked","done","unknown"}
try: r=json.load(sys.stdin)["result"]["pane"].get("agent_status")
except Exception: sys.exit(1)
print("unknown" if r is None else r if isinstance(r,str) and r in V else sys.exit(1))') \
    || { echo "status parse failed / off-enum for $pane" >&2; exit 1; }
  case "$st" in
    done|idle) settled="$st"; break ;;
    blocked) echo "$pane: BLOCKED — a human must answer a dialog" >&2; exit 3 ;;
    working) herdr wait agent-status "$pane" --status done --timeout 15000 \
               || herdr wait agent-status "$pane" --status idle --timeout 15000 || true ;;
    *) sleep 2 ;;
  esac
done
[ -n "$settled" ] || { echo "$pane: TIMEOUT before completion" >&2; exit 2; }
echo "settled:$settled"
```

`scripts/wait_for_idle.py` defaults to **post-send** semantics. Capture `--baseline-file` before send and arrange `--completion-marker`; this closes both races: a fast reply cannot become the baseline, and stable prompt echo cannot look complete. Without a marker, content stability remains a legacy heuristic fallback. Use `--ready` only for boot waits.

## Blocked

`blocked` is **not** success. Typical causes: workspace trust, API key, permission prompt, plan-mode confirmation.

Rules:

- Never send the next task while blocked (it becomes menu input).
- `herdr agent focus <name>` so the human sees the dialog.
- After the human resolves it, re-check status, then continue.

## Timeouts and anti-deadloop

Set budgets before waiting:

| Budget | Suggested default |
|---|---|
| Boot to idle | 60s |
| Delivery → working | 15s |
| Task completion | 180s (tune per task) |
| Re-waits after timeout | max 2–3, then escalate |

On timeout:

1. `herdr pane get "$pane"`
2. `herdr pane read "$pane" --source recent-unwrapped --lines 80`
3. `herdr agent explain "$pane"` if status looks wrong
4. Report stall to the user — do **not** loop forever

## When status is `unknown`

Integrations missing or exotic CLI:

1. `herdr integration install <agent>` when supported
2. Fall back to content stability: `python3 "$here/wait_for_idle.py" <pane_id>` (`$here` = resolved scripts/ dir — probe install locations, not `$0`)
3. Still use capped `pane read` for the reply

The helper mirrors tmux-agent-comms' wait semantics (exit 0 idle / 2 timeout / 3 blocked markers) but reads via `herdr pane read` instead of `tmux capture-pane`.

## Concurrent fleet waits

Capture every baseline first, then send all, then wait concurrently. This order handles agents that finish before their waiter process starts.

**Precondition:** `$panes` here must already be the deduped, **preflighted** target set — every entry passed the fail-closed working/blocked/unverifiable check (as `scripts/broadcast.sh` Phase 1b and the manual fleet recipe in `references/herdr-recipes.md` build it). Don't `pane run` a raw target list; a working/blocked/off-enum pane would be sent into blind. These illustrative loops send straight after baselining, so a target that turns working/blocked in that window is sent into anyway — prefer `scripts/broadcast.sh`, which **rechecks each target's status immediately before its dispatch** and skips any that became unsafe.

```bash
tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT   # cleanup regardless of how we exit
markers=()
tasks=()
for i in "${!panes[@]}"; do
  # Guard each baseline read — a silent failure here would poison the wait.
  herdr pane read "${panes[$i]}" --source recent-unwrapped --lines 80 >"$tmpdir/$i.baseline" \
    || { echo "Error: baseline read failed for ${panes[$i]}" >&2; exit 1; }
  suffix="$(date +%s)_$$_${i}_$RANDOM"
  markers+=("HERDR_DONE_$suffix")
  tasks[$i]="$msg

After fully finishing, concatenate and print: HERDR_DONE_ and $suffix"
done
# Send to all; a failed send must be recorded, not ignored.
send_failed=()
for i in "${!panes[@]}"; do
  herdr pane run "${panes[$i]}" "${tasks[$i]}" || send_failed+=("${panes[$i]}")
done
# Wait concurrently, but capture EACH waiter's exit status (a bare `wait`
# returns 0 for the shell even if a waiter timed out or hit `blocked`).
pids=()
for i in "${!panes[@]}"; do
  python3 "$here/wait_for_idle.py" "${panes[$i]}" --timeout 180 --lines 80 \
    --baseline-file "$tmpdir/$i.baseline" --completion-marker "${markers[$i]}" &
  pids+=("$!:${panes[$i]}")
done
overall=0
for e in "${pids[@]}"; do
  jp="${e%%:*}"; pane="${e#*:}"
  if wait "$jp"; then
    echo "$pane: reply ready"
  else
    rc=$?
    case "$rc" in
      3) echo "$pane: BLOCKED — a human must answer a dialog" >&2 ;;
      2) echo "$pane: TIMEOUT before completion" >&2 ;;
      *) echo "$pane: waiter failed (rc $rc)" >&2 ;;
    esac
    overall=1
  fi
done
if [ "${#send_failed[@]}" -gt 0 ]; then
  echo "Send failed for: ${send_failed[*]}" >&2
  overall=1
fi
exit "$overall"   # non-zero if any send failed or any waiter didn't complete
```

Or with raw waits — **do not** wait only on `done` (focused fleet tabs usually finish as `idle`):

```bash
send_failed=()
for p in "${panes[@]}"; do herdr pane run "$p" "$msg" || send_failed+=("$p"); done
pids=()
for p in "${panes[@]}"; do
  (
    deadline=$((SECONDS + 180))
    while (( SECONDS < deadline )); do
      # Guard the status read — a failed `herdr pane get` must not be treated
      # as an empty status that falls through to `sleep`; exit as an error.
      out=$(herdr pane get "$p" 2>/dev/null) || exit 4
      st=$(printf '%s' "$out" | python3 -c 'import sys,json
V={"idle","working","blocked","done","unknown"}
try: r=json.load(sys.stdin)["result"]["pane"].get("agent_status")
except Exception: sys.exit(1)
print("unknown" if r is None else r if isinstance(r,str) and r in V else sys.exit(1))') || exit 4
      case "$st" in
        done|idle) exit 0 ;;
        blocked) exit 3 ;;
        working) herdr wait agent-status "$p" --status done --timeout 15000 \
                   || herdr wait agent-status "$p" --status idle --timeout 15000 || true ;;
        *) sleep 2 ;;
      esac
    done
    exit 2
  ) &
  pids+=("$!:$p")
done
overall=0
for e in "${pids[@]}"; do
  jp="${e%%:*}"; pane="${e#*:}"
  wait "$jp" || { rc=$?; overall=1
    case "$rc" in 3) echo "$pane: BLOCKED (human needed)" >&2 ;;
                  4) echo "$pane: status lookup failed" >&2 ;;
                  *) echo "$pane: not ready (rc $rc)" >&2 ;; esac; }
done
[ "${#send_failed[@]}" -eq 0 ] || { echo "Send failed: ${send_failed[*]}" >&2; overall=1; }
exit "$overall"
```

Or simply: `scripts/broadcast.sh "$msg" reviewer tests docs`.

Serializing full send→wait→read per agent makes total time the sum of agents; concurrent waits make it the max.

## Manual verify before high-stakes relay

Status is advisory relative to your goal. Before the user acts on a result:

```bash
herdr pane read "$pane" --source recent-unwrapped --lines 40 > /tmp/a.txt
sleep 3
herdr pane read "$pane" --source recent-unwrapped --lines 40 > /tmp/b.txt
cmp -s /tmp/a.txt /tmp/b.txt && echo stable || echo still-changing
```

Still-changing or spinner chrome → keep waiting. Stable + no blocked markers → safe to relay.
