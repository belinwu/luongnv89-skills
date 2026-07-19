#!/usr/bin/env bash
# Broadcast one message to several Herdr agents, then collect each reply.
#
# Sends to EVERY target first (fast), then waits on all of them CONCURRENTLY.
# Wall-clock is the slowest single agent, not the sum.
#
# Usage:
#   scripts/broadcast.sh "message" target1 target2 [target3 ...]
#
# Targets: agent names (reviewer) or pane ids (w26:p4)
#
# Options (env vars):
#   HAC_TIMEOUT       per-agent wait timeout in seconds (default: 180)
#   HAC_LINES         transcript lines used for baseline + reply (default: 60)
#   HAC_WAIT_ARGS     extra args passed to wait_for_idle.py (e.g. "--full")
#
# Exit 0 if all agents settled idle/done; otherwise 1.

set -u

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
waiter="$here/wait_for_idle.py"
timeout="${HAC_TIMEOUT:-180}"
lines="${HAC_LINES:-60}"

if [ "$#" -lt 2 ]; then
  echo "Error: need a message and at least one target." >&2
  echo "Usage: scripts/broadcast.sh \"message\" target1 [target2 ...]" >&2
  exit 1
fi
if ! command -v herdr >/dev/null 2>&1; then
  echo "Error: herdr is not installed or not on PATH." >&2
  exit 1
fi
if [ ! -f "$waiter" ]; then
  echo "Error: helper not found at $waiter — run broadcast.sh from the skill dir." >&2
  exit 1
fi

msg="$1"; shift
targets=("$@")

resolve_pane() {
  local t="$1"
  if herdr pane get "$t" >/dev/null 2>&1; then
    printf '%s\n' "$t"
    return 0
  fi
  herdr agent get "$t" 2>/dev/null | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
    a = d.get("result", {}).get("agent") or d.get("result", {})
    print(a["pane_id"])
except Exception:
    sys.exit(1)
'
}

pane_status() {
  # Print the pane's agent_status and return 0 ONLY when the lookup+parse
  # actually succeeded. A failed `herdr pane get` or malformed JSON must
  # return non-zero (NOT an empty "safe" status) so the caller can reject the
  # target instead of sending into an unverifiable pane. A validly-absent
  # status field prints "unknown" (non-integrated CLIs report that normally).
  local out
  out="$(herdr pane get "$1" 2>/dev/null)" || return 1
  printf '%s' "$out" | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
    pane = d["result"]["pane"]
except Exception:
    sys.exit(1)   # lookup/parse failure — NOT a safe empty status
print(pane.get("agent_status") or "unknown")
'
}

# Phase 1: resolve all targets first, deduping by pane id so a name and its
# pane-id alias (e.g. "reviewer" and "w26:p4") don't double-send.
# (Plain arrays + linear scan, not associative arrays: this needs to run on
# bash 3.2 too, e.g. macOS's default /bin/bash.)
panes=()
labels=()
missing=()
for t in "${targets[@]}"; do
  if p="$(resolve_pane "$t")"; then
    dup=""
    for existing in "${panes[@]+"${panes[@]}"}"; do
      if [ "$existing" = "$p" ]; then
        dup=1
        break
      fi
    done
    if [ -n "$dup" ]; then
      echo "Note: '$t' resolves to an already-targeted pane $p — skipping duplicate." >&2
      continue
    fi
    panes+=("$p")
    labels+=("$t")
  else
    missing+=("$t")
  fi
done
if [ "${#missing[@]}" -gt 0 ]; then
  echo "Error: these targets don't resolve: ${missing[*]}" >&2
  echo "List them with: herdr agent list" >&2
  exit 1
fi

# Phase 1b: reject panes that aren't safely sendable before we send.
# - `working`: did not start working because of THIS broadcast, so waiting on
#   it afterward cannot reliably distinguish this send's completion from the
#   prior task's.
# - `blocked`: a trust/auth/permission dialog is on screen. Typing the task
#   into that dialog would submit garbage to the prompt, not the agent — skip
#   it and surface the dialog instead (Critical Rule 7 in SKILL.md).
# Skip both rather than risk a false "settled" report or a swallowed dialog.
busy=()
blocked=()
unverifiable=()
ready_panes=()
ready_labels=()
for i in "${!panes[@]}"; do
  # A failed status lookup must NOT fall through as "safe to send" — reject
  # the target rather than risk sending into a working/blocked pane whose
  # state we couldn't confirm.
  if ! st="$(pane_status "${panes[$i]}")"; then
    unverifiable+=("${labels[$i]} (${panes[$i]})")
    continue
  fi
  if [ "$st" = "working" ]; then
    busy+=("${labels[$i]} (${panes[$i]})")
    continue
  fi
  if [ "$st" = "blocked" ]; then
    blocked+=("${labels[$i]} (${panes[$i]})")
    continue
  fi
  # idle / done / unknown (validly reported) are sendable.
  ready_panes+=("${panes[$i]}")
  ready_labels+=("${labels[$i]}")
done
if [ "${#busy[@]}" -gt 0 ]; then
  echo "Error: these targets are already working and were skipped: ${busy[*]}" >&2
  echo "Wait for them to go idle/done first, or target only the idle agents." >&2
fi
if [ "${#blocked[@]}" -gt 0 ]; then
  echo "Error: these targets are blocked (trust/auth dialog) and were skipped: ${blocked[*]}" >&2
  echo "A human must answer the dialog first — see: herdr agent focus <name>." >&2
fi
if [ "${#unverifiable[@]}" -gt 0 ]; then
  echo "Error: could not verify status for these targets (lookup/parse failed) and skipped them: ${unverifiable[*]}" >&2
  echo "Refusing to send into a pane whose working/blocked state is unknown — check 'herdr pane get <id>'." >&2
fi
panes=("${ready_panes[@]+"${ready_panes[@]}"}")
labels=("${ready_labels[@]+"${ready_labels[@]}"}")
if [ "${#panes[@]}" -eq 0 ]; then
  echo "Error: no targets left to send to." >&2
  exit 1
fi

# Phase 2: snapshot every pane BEFORE send. A fast agent can finish before its
# waiter starts; stable output after this baseline still proves new activity.
tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/hac_broadcast.XXXXXX")"
trap 'rm -rf "$tmpdir"' EXIT
for i in "${!panes[@]}"; do
  if ! herdr pane read "${panes[$i]}" --source recent-unwrapped --lines "$lines" \
    >"$tmpdir/$i.baseline"; then
    echo "Error: could not capture baseline for ${panes[$i]}" >&2
    exit 1
  fi
done

# Phase 3: fan out. The full marker is deliberately absent from the prompt:
# prompt echo contains its two halves; only the completed reply joins them.
#
# A failed `pane run` here must NOT abort the whole broadcast: panes sent
# to earlier in this loop are already mid-task, and abandoning them without
# a wait/report would silently drop results the caller has no way to
# recover. Record the failure and keep going; only successfully-dispatched
# panes proceed to Phase 4.
markers=()
send_failed=()
for i in "${!panes[@]}"; do
  p="${panes[$i]}"
  suffix="$(date +%s)_$$_${i}_${RANDOM}"
  markers[$i]="HERDR_DONE_$suffix"
  task="$msg

After fully finishing the task, concatenate and print these two parts without spaces: HERDR_DONE_ and $suffix"
  if ! herdr pane run "$p" "$task" >/dev/null; then
    echo "Error: pane run failed for ${labels[$i]} ($p) — dispatch stopped for this target, already-sent panes still awaited." >&2
    send_failed+=("$i")
  fi
done

# Phase 4: wait concurrently, but only on panes the send actually reached.
pids=()
wait_indices=()
for i in "${!panes[@]}"; do
  skip=""
  for f in "${send_failed[@]+"${send_failed[@]}"}"; do
    [ "$f" = "$i" ] && { skip=1; break; }
  done
  [ -n "$skip" ] && continue
  p="${panes[$i]}"
  wait_indices+=("$i")
  # shellcheck disable=SC2086
  (
    python3 "$waiter" "$p" --timeout "$timeout" ${HAC_WAIT_ARGS:-} \
      --lines "$lines" --baseline-file "$tmpdir/$i.baseline" \
      --completion-marker "${markers[$i]}" \
      >"$tmpdir/$i.out" 2>"$tmpdir/$i.err"
    echo "$?" >"$tmpdir/$i.code"
  ) &
  pids+=("$!")
done
for pid in "${pids[@]+"${pids[@]}"}"; do wait "$pid"; done

# Phase 5: emit labeled blocks — dispatched panes first (settled/timeout/
# blocked/error), then a distinct block per pane that never got a send.
overall=0
# Any pane we could NOT safely deliver to fails the broadcast — including
# `unverifiable` targets (status lookup/parse failed). Omitting them here made
# a mixed bad+good broadcast exit 0 even though some targets were skipped.
if [ "${#busy[@]}" -gt 0 ] || [ "${#blocked[@]}" -gt 0 ] \
   || [ "${#unverifiable[@]}" -gt 0 ] || [ "${#send_failed[@]}" -gt 0 ]; then
  overall=1
fi
for i in "${wait_indices[@]+"${wait_indices[@]}"}"; do
  label="${labels[$i]}"
  p="${panes[$i]}"
  code="$(cat "$tmpdir/$i.code" 2>/dev/null || echo "?")"
  case "$code" in
    0) state="idle/done" ;;
    2) state="TIMEOUT"; overall=1 ;;
    3) state="BLOCKED (needs human)"; overall=1 ;;
    *) state="error"; overall=1 ;;
  esac
  echo "===== $label ($p) [$state, exit $code] ====="
  cat "$tmpdir/$i.out" 2>/dev/null
  if [ "$code" != "0" ]; then
    cat "$tmpdir/$i.err" 2>/dev/null >&2
  fi
  echo
done
for i in "${send_failed[@]+"${send_failed[@]}"}"; do
  echo "===== ${labels[$i]} (${panes[$i]}) [SEND-FAILED, not waited] =====" >&2
done

if [ "${#send_failed[@]}" -gt 0 ]; then
  echo "Partial results: ${#send_failed[@]} of ${#panes[@]} target(s) never received the message (see SEND-FAILED above). Results above are only for targets successfully dispatched." >&2
fi

exit "$overall"
