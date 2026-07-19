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

`$here` below is the skill's `scripts/` dir, resolved executably (repo-local first, then `.agents/`, `.claude/`, `$HOME`; fail fast if none resolve — matching SKILL.md Phase 4/5).

```bash
here=""
for cand in "skills/herdr-agent-comms/scripts" ".agents/skills/herdr-agent-comms/scripts" \
  ".claude/skills/herdr-agent-comms/scripts" "$HOME/.claude/skills/herdr-agent-comms/scripts" \
  "$HOME/.agents/skills/herdr-agent-comms/scripts"; do
  [ -f "$cand/preflight_send.py" ] && { here="$cand"; break; }
done
[ -n "$here" ] || { echo "Error: preflight_send.py not found in any known install location" >&2; exit 1; }
baseline="$(mktemp)"
herdr pane read "$pane" --source recent-unwrapped --lines 80 >"$baseline" \
  || { echo "Error: baseline read failed for $pane" >&2; exit 1; }
suffix="$(date +%s)_$$_$RANDOM"
completion_marker="HERDR_DONE_$suffix"
task="do the thing

After fully finishing, concatenate and print these parts without spaces: HERDR_DONE_ and $suffix"
# FAIL-CLOSED preflight IMMEDIATELY before dispatch — the single-target twin of
# broadcast.sh's pre-dispatch recheck. Placed here (not before baseline/task
# prep) so a target that turned working/blocked during that prep can't still be
# sent into. Refuse to type into a working (rc 2), blocked (rc 3), or
# unverifiable/off-enum (rc 4) pane; only idle/done/unknown (rc 0) is safe —
# skipping it let a task land in a blocked trust dialog and report success.
python3 "$here/preflight_send.py" "$pane" >/dev/null \
  || { echo "Error: $pane not safe to send to (preflight failed) — see stderr" >&2; rm -f "$baseline"; exit 1; }
herdr pane run "$pane" "$task" || { echo "Error: send failed for $pane" >&2; rm -f "$baseline"; exit 1; }
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
    python3 "$here/preflight_send.py" "$pane" >/dev/null \
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

Pick **exactly one** of the two waiters below — they are mutually exclusive, not sequential. Both consume the pre-send `$baseline` + `$completion_marker`; whichever you run owns the `$baseline` cleanup, so the other must not have deleted it first.

**Preferred — the helper** (post-send semantics; the pre-send baseline closes the fast-completion race):

```bash
# Resolve $here = scripts/ dir executably (don't derive from $0/BASH_SOURCE).
# Repo-local copies win over global installs; fail fast if none resolve:
here=""
for cand in "skills/herdr-agent-comms/scripts" ".agents/skills/herdr-agent-comms/scripts" \
  ".claude/skills/herdr-agent-comms/scripts" "$HOME/.claude/skills/herdr-agent-comms/scripts" \
  "$HOME/.agents/skills/herdr-agent-comms/scripts"; do
  [ -f "$cand/wait_for_idle.py" ] && { here="$cand"; break; }
done
[ -n "$here" ] || { echo "Error: wait_for_idle.py not found in any known install location" >&2; exit 1; }
python3 "$here/wait_for_idle.py" "$pane" --timeout 180 --lines 80 \
  --baseline-file "$baseline" --completion-marker "$completion_marker"
rc=$?               # capture BEFORE cleanup — `rm` would clobber $?
rm -f "$baseline"   # this path is done with the baseline now
# Act on the waiter's exit and PROPAGATE it — 0 done/idle, 1 error, 2 timeout,
# 3 blocked. Any non-zero means no delivered reply.
case "$rc" in
  0) echo "settled" ;;
  3) echo "$pane: BLOCKED — a human must answer a dialog" >&2; exit 3 ;;
  2) echo "$pane: TIMEOUT before completion" >&2; exit 2 ;;
  *) echo "$pane: waiter failed (rc $rc)" >&2; exit "$rc" ;;
esac
```

**OR — helper-free** (no `wait_for_idle.py`; run this INSTEAD of the block above, so the baseline still exists). A hand-rolled `pane get` poll must NOT accept the first idle/done it sees: a pane idle BEFORE the task started (send not yet landed, or a prior fast task) would be a FALSE completion for THIS send. Gate acceptance on having first observed `working` (or a fresh completion marker absent from the pre-send baseline); `blocked` exits 3, deadline exhaustion exits 2. A single `rm -f "$baseline"` runs after the loop, on every exit path:

```bash
deadline=$((SECONDS + 180)); settled=""; saw_working=""; rc=0
while (( SECONDS < deadline )); do
  out=$(herdr pane get "$pane" 2>/dev/null) || { echo "status lookup failed for $pane" >&2; rc=1; break; }
  st=$(printf '%s' "$out" | python3 -c 'import sys,json
V={"idle","working","blocked","done","unknown"}
try: r=json.load(sys.stdin)["result"]["pane"].get("agent_status")
except Exception: sys.exit(1)
print("unknown" if r is None else r if isinstance(r,str) and r in V else sys.exit(1))') \
    || { echo "status parse failed / off-enum for $pane" >&2; rc=1; break; }
  # A fresh joined marker in the transcript (not in the baseline) also proves
  # completion even if we never caught the `working` window.
  if grep -qF "$completion_marker" <(herdr pane read "$pane" --source recent-unwrapped --lines 80 2>/dev/null) \
     && ! grep -qF "$completion_marker" "$baseline"; then
    settled="marker"; break
  fi
  case "$st" in
    working) saw_working=1
             herdr wait agent-status "$pane" --status done --timeout 15000 \
               || herdr wait agent-status "$pane" --status idle --timeout 15000 || true ;;
    done|idle) [ -n "$saw_working" ] && { settled="$st"; break; }  # else pre-task idle: keep waiting
               sleep 2 ;;
    blocked) echo "$pane: BLOCKED — a human must answer a dialog" >&2; rc=3; break ;;
    *) sleep 2 ;;
  esac
done
rm -f "$baseline"   # single cleanup, reached on every exit path
[ "$rc" -eq 0 ] || exit "$rc"
[ -n "$settled" ] || { echo "$pane: TIMEOUT before completion (never saw working / fresh marker)" >&2; exit 2; }
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

**Precondition:** `$panes` here must already be the deduped, **preflighted** target set — every entry passed the fail-closed working/blocked/unverifiable check (as `scripts/broadcast.sh` Phase 1b and the manual fleet recipe in `references/herdr-recipes.md` build it). Don't `pane run` a raw target list; a working/blocked/off-enum pane would be sent into blind. The first loop below **rechecks each target's status immediately before its dispatch** and skips any that became working/blocked/unverifiable in the baseline→send window — matching `scripts/broadcast.sh`. Still prefer `scripts/broadcast.sh` for real use; these loops are illustrative.

```bash
# Resolve $here = scripts/ dir executably (repo-local first; fail fast).
here=""
for cand in "skills/herdr-agent-comms/scripts" ".agents/skills/herdr-agent-comms/scripts" \
  ".claude/skills/herdr-agent-comms/scripts" "$HOME/.claude/skills/herdr-agent-comms/scripts" \
  "$HOME/.agents/skills/herdr-agent-comms/scripts"; do
  [ -f "$cand/wait_for_idle.py" ] && { here="$cand"; break; }
done
[ -n "$here" ] || { echo "Error: wait_for_idle.py not found in any known install location" >&2; exit 1; }
# Fail-closed, enum-validated status probe (returns non-zero on lookup/parse
# failure or an off-enum value) — the same check broadcast.sh runs.
pane_status() { local out
  out="$(herdr pane get "$1" 2>/dev/null)" || return 1
  printf '%s' "$out" | python3 -c 'import sys,json
V={"idle","working","blocked","done","unknown"}
try: r=json.load(sys.stdin)["result"]["pane"].get("agent_status")
except Exception: sys.exit(1)
print("unknown" if r is None else r if isinstance(r,str) and r in V else sys.exit(1))'; }

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
# Send to all. RECHECK status immediately before each dispatch (matching
# broadcast.sh): the preflight/baseline loop above ran earlier, so a target may
# have turned working/blocked (or become unverifiable) since — skip it rather
# than send blind. Record send failures and became-unsafe skips BY INDEX so the
# wait loop can exclude both (a name-keyed list can't be matched against $i).
send_failed=(); became_unsafe=()
for i in "${!panes[@]}"; do
  if ! st="$(pane_status "${panes[$i]}")" \
     || [ "$st" = "working" ] || [ "$st" = "blocked" ]; then
    echo "Error: ${panes[$i]} became unsafe (${st:-unverifiable}) before dispatch — skipped." >&2
    became_unsafe+=("$i"); continue
  fi
  herdr pane run "${panes[$i]}" "${tasks[$i]}" || send_failed+=("$i")
done
# Wait concurrently on dispatched panes only (exclude send_failed AND
# became_unsafe), capturing EACH waiter's exit status (a bare `wait` returns 0
# for the shell even if a waiter timed out or hit `blocked`).
pids=()
for i in "${!panes[@]}"; do
  skip=""
  for f in ${send_failed[@]+"${send_failed[@]}"} ${became_unsafe[@]+"${became_unsafe[@]}"}; do
    [ "$f" = "$i" ] && { skip=1; break; }
  done
  [ -n "$skip" ] && continue
  python3 "$here/wait_for_idle.py" "${panes[$i]}" --timeout 180 --lines 80 \
    --baseline-file "$tmpdir/$i.baseline" --completion-marker "${markers[$i]}" &
  pids+=("$!:${panes[$i]}")
done
overall=0
for e in "${pids[@]+"${pids[@]}"}"; do
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
  for i in "${send_failed[@]}"; do echo "Send failed for: ${panes[$i]}" >&2; done
  overall=1
fi
[ "${#became_unsafe[@]}" -eq 0 ] || overall=1
exit "$overall"   # non-zero if any send/preflight failed or any waiter didn't complete
```

Or with raw waits — **do not** wait only on `done` (focused fleet tabs usually finish as `idle`):

```bash
_status() { local out; out="$(herdr pane get "$1" 2>/dev/null)" || return 1
  printf '%s' "$out" | python3 -c 'import sys,json
V={"idle","working","blocked","done","unknown"}
try: r=json.load(sys.stdin)["result"]["pane"].get("agent_status")
except Exception: sys.exit(1)
print("unknown" if r is None else r if isinstance(r,str) and r in V else sys.exit(1))'; }
send_failed=(); unsafe=()
for p in "${panes[@]}"; do
  # Recheck immediately before dispatch (matching broadcast.sh); skip if it
  # turned working/blocked/unverifiable since the preflight.
  if ! st="$(_status "$p")" || [ "$st" = working ] || [ "$st" = blocked ]; then
    echo "Error: $p became unsafe (${st:-unverifiable}) before dispatch — skipped." >&2
    unsafe+=("$p"); continue
  fi
  herdr pane run "$p" "$msg" || send_failed+=("$p")
done
# Build the wait set: dispatched panes only (exclude send_failed and unsafe).
wait_panes=()
for p in "${panes[@]}"; do
  drop=""
  for b in ${send_failed[@]+"${send_failed[@]}"} ${unsafe[@]+"${unsafe[@]}"}; do
    [ "$b" = "$p" ] && { drop=1; break; }
  done
  [ -n "$drop" ] || wait_panes+=("$p")
done
pids=()
for p in ${wait_panes[@]+"${wait_panes[@]}"}; do
  (
    deadline=$((SECONDS + 180)); saw_working=""
    while (( SECONDS < deadline )); do
      out=$(herdr pane get "$p" 2>/dev/null) || exit 4   # fail-closed status read
      st=$(printf '%s' "$out" | python3 -c 'import sys,json
V={"idle","working","blocked","done","unknown"}
try: r=json.load(sys.stdin)["result"]["pane"].get("agent_status")
except Exception: sys.exit(1)
print("unknown" if r is None else r if isinstance(r,str) and r in V else sys.exit(1))') || exit 4
      case "$st" in
        # Accept idle/done ONLY after a `working` transition — a pane idle before
        # the task landed would otherwise be a false completion for THIS send.
        done|idle) [ -n "$saw_working" ] && exit 0; sleep 2 ;;
        blocked) exit 3 ;;
        working) saw_working=1
                 herdr wait agent-status "$p" --status done --timeout 15000 \
                   || herdr wait agent-status "$p" --status idle --timeout 15000 || true ;;
        *) sleep 2 ;;
      esac
    done
    exit 2
  ) &
  pids+=("$!:$p")
done
overall=0
for e in ${pids[@]+"${pids[@]}"}; do
  jp="${e%%:*}"; pane="${e#*:}"
  wait "$jp" || { rc=$?; overall=1
    case "$rc" in 3) echo "$pane: BLOCKED (human needed)" >&2 ;;
                  4) echo "$pane: status lookup failed" >&2 ;;
                  2) echo "$pane: TIMEOUT (never saw working)" >&2 ;;
                  *) echo "$pane: not ready (rc $rc)" >&2 ;; esac; }
done
[ "${#send_failed[@]}" -eq 0 ] || { echo "Send failed: ${send_failed[*]}" >&2; overall=1; }
[ "${#unsafe[@]}" -eq 0 ] || overall=1
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
