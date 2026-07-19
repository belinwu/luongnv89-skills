# Herdr recipes for agent fleets

Read this when you need layout variants, multi-line sends, human steer/focus, scrollback recovery, or troubleshooting.

## Default fleet layout (this skill)

**Root + sub-agents as equal-width columns in one tab:**

```
Session (default)
└── Workspace: <project>
    └── Tab: <root's tab>                          ← single row of columns
        ┌───────────┬───────────┬───────────┐
        │ root (you)│ reviewer  │ tests      │
        └───────────┴───────────┴───────────┘
```

(`next_grid_split.py` always targets the current rightmost column and plans
a resize for every column, so root and every sub-agent stay the same width
no matter how many are spawned — never a wide root next to narrow workers,
or vice versa.)

Why this default: the human sees the **root agent and every sub-agent at the
same size**; the orchestrator is never displaced into a side tab or left
oddly wide/narrow; sidebar still rolls status per workspace.

### Spawn N sub-agents into an equal-width grid

Use `scripts/next_grid_split.py` before every split: it always targets the
**current rightmost column** and emits a full plan — the split ratio for the
new pane, plus a resize line for every existing column so all of them
(including root) converge to the same `1/N` share.

```bash
root_pane="${HERDR_PANE_ID:?}"
root_tab="${HERDR_TAB_ID:?}"
ws="${HERDR_WORKSPACE_ID:?}"
project_dir=$(pwd)
# Resolve scripts/ by probing known install locations. Don't derive from
# $0/BASH_SOURCE here — unreliable when an agent runs this inline rather
# than as a saved script file. Repo-local copies win over global installs
# so a pinned repo checkout isn't silently overridden by whatever version
# happens to be installed globally.
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

spawn_sub() {
  local name=$1 cmd=$2
  local plan split_from ratio j pane
  herdr agent list | grep -q "\"name\":\"$name\"" && name="${name}-$(date +%s)"
  # plan: line 1 "split <rightmost> right --ratio <share>", rest "resize <pane> <share>"
  plan=$(python3 "$here/next_grid_split.py" --root-pane "$root_pane")
  read -r _ split_from _ _ ratio < <(head -1 <<<"$plan")
  j=$(herdr pane split "$split_from" --direction right --ratio "$ratio" --cwd "$project_dir" --no-focus)
  pane=$(printf '%s' "$j" | python3 -c 'import sys,json; d=json.load(sys.stdin); r=d["result"]; print((r.get("pane") or r)["pane_id"])')
  tail -n +2 <<<"$plan" | while read -r _ pid share; do
    [ "$pid" = "$pane" ] && continue
    herdr pane resize --pane "$pid" --direction right --amount "$share" >/dev/null || true
  done
  herdr pane rename "$pane" "$name" >/dev/null
  herdr agent rename "$pane" "$name" >/dev/null
  herdr pane run "$pane" "$cmd" >/dev/null
  printf '%s\n' "$pane"
}

p_reviewer=$(spawn_sub reviewer "pi --thinking medium")
p_tests=$(spawn_sub tests "pi --thinking low")
# optional third: spawn_sub docs "pi --thinking low"
```

### Grid heuristics

| Step | Rule |
|---|---|
| Target pane | current rightmost column (`rect.x` order) |
| Direction | always `right` — one row of columns, never `down` |
| After each spawn | resize **every** column (including root) to `1/N`, N = new column count |
| Re-run per spawn | never hardcode a fixed ratio/amount — it shrinks every time |
| Focus | always `--no-focus` |

```bash
# $here from the resolver above (or re-probe if starting fresh in this shell)
python3 "$here/next_grid_split.py" --root-pane "$root_pane"
herdr pane layout --pane "$root_pane"   # verify equal-width rects
```

Manual fallback without the helper: read `herdr pane layout`, order panes by `rect.x`, split the rightmost one `right`, then resize every column (new + pre-existing) to `1 / (existing_count + 1)`.

**Verification caveat:** `herdr pane split --ratio` / `herdr pane resize --amount` semantics (fraction of remaining space vs. absolute tab fraction) are not confirmed against a live `herdr` server by this skill's tests. Check `herdr pane layout` after a spawn to confirm the rects actually came out equal width.

### Prefer grid split over `agent start`

| Command | When |
|---|---|
| `next_grid_split.py` + `herdr pane split` + `herdr pane resize` … `--no-focus` | **Default** — equal-width grid including root |
| `herdr agent start name --tab "$root_tab" --split right --no-focus -- …` | OK if you only care about same tab; leaves unequal widths unless you resize manually afterward |

### When to use tab-per-agent instead

- User asks for "full screen per agent" / "own tab each"
- Agent TUIs need a wide viewport (diff-heavy review)
- More agents than fit usefully in one tile (~5+)

```bash
for name in reviewer tests docs; do
  j=$(herdr tab create --workspace "$ws" --cwd "$project_dir" --label "$name" --no-focus)
  pane=$(printf '%s' "$j" | python3 -c 'import sys,json; print(json.load(sys.stdin)["result"]["root_pane"]["pane_id"])')
  herdr pane rename "$pane" "$name"
  herdr agent rename "$pane" "$name"
  herdr pane run "$pane" "pi --thinking medium"
done
```

### Adding a log / shell pane into the grid

```bash
# $here from the resolver above (or re-probe if starting fresh in this shell)
plan=$(python3 "$here/next_grid_split.py" --root-pane "$root_pane")
read -r _ split_from _ _ ratio < <(head -1 <<<"$plan")
j=$(herdr pane split "$split_from" --direction right --ratio "$ratio" --cwd "$project_dir" --no-focus)
pane=$(printf '%s' "$j" | python3 -c 'import sys,json; d=json.load(sys.stdin); r=d["result"]; print((r.get("pane") or r)["pane_id"])')
tail -n +2 <<<"$plan" | while read -r _ pid share; do
  [ "$pid" = "$pane" ] && continue
  herdr pane resize --pane "$pid" --direction right --amount "$share" >/dev/null || true
done
herdr pane rename "$pane" logs
herdr pane run "$pane" "bash -lc 'tail -f /tmp/app.log'"
```

## Sending multi-line or code-heavy messages

`herdr pane run <pane> <command>` takes one shell-quoted string. Nested quotes and newlines break easily.

**Pattern A — short instruction that reads a file:**

```bash
task_file=$(mktemp)
cat >"$task_file" <<'EOF'
Review these files:
- src/a.ts
- src/b.ts

Return only:
1. bugs
2. missing tests
EOF
herdr pane run "$pane_id" "Read $task_file and follow its instructions. Delete the file when done."
```

**Pattern B — `send-text` then Enter** (when you must avoid shell expansion inside `pane run`):

```bash
herdr pane send-text "$pane_id" "line one"
herdr pane send-keys "$pane_id" enter
```

**Pattern C — agent name:**

```bash
herdr agent send reviewer "summarize src/"
herdr pane send-keys "$pane_id" enter
```

Remember: `agent send` does **not** append Enter; `pane run` does.

## Human steer / focus

| Goal | Command |
|---|---|
| Stay on whole board | already one tab (root + subs) |
| Jump UI to one sub-agent | `herdr agent focus reviewer` |
| Jump back toward root | click root pane / focus root pane id |
| Attach/takeover terminal | `herdr agent attach reviewer` (optional `--takeover`) |
| Read without stealing focus | `herdr agent read reviewer --source recent-unwrapped --lines 80` |

Orchestrator rule: use `--no-focus` on every split/start so fleet spawn doesn't yank focus off the root agent. Focus a sub-agent only when the human wants to type or dismiss a `blocked` dialog.

Detach Herdr client (leave agents running): `prefix+q` (`ctrl+b` then `q`). Reattach: `herdr` in a terminal.

## Reading scrollback robustly

```bash
herdr pane read "$pane_id" --source recent-unwrapped --lines 80
herdr pane read "$pane_id" --source recent-unwrapped --lines 200
herdr pane read "$pane_id" --source visible --lines 50
herdr pane read "$pane_id" --source detection
```

Prefer `recent-unwrapped` for agent transcripts. Widen `--lines` stepwise if truncated.

## Broadcast pattern (manual)

Prefer `scripts/broadcast.sh` — it already resolves paths, dedupes, and rejects
busy/blocked panes. The manual equivalent below exists for when the script is
unavailable and must **replicate the same safeguards**, not skip them:

```bash
# Repo-local copies win over global installs (see Phase 2a). Fail fast if
# unresolved — do not silently continue with an empty $here.
here=""
for cand in \
  "skills/herdr-agent-comms/scripts" \
  ".agents/skills/herdr-agent-comms/scripts" \
  ".claude/skills/herdr-agent-comms/scripts" \
  "$HOME/.claude/skills/herdr-agent-comms/scripts" \
  "$HOME/.agents/skills/herdr-agent-comms/scripts"; do
  if [ -f "$cand/wait_for_idle.py" ]; then here="$cand"; break; fi
done
[ -n "$here" ] || { echo "Error: wait_for_idle.py not found in any known install location (repo, .agents/, .claude/, \$HOME). Fix the install or set \$here manually before retrying." >&2; exit 1; }

targets=(reviewer tests docs)
msg="Pull latest main and report branch + dirty state."

# Resolve names → pane ids, deduping so a name and its own pane-id alias
# (e.g. "reviewer" and "w26:p4") don't double-send.
panes=(); labels=()
for t in "${targets[@]}"; do
  p=$(herdr agent get "$t" | python3 -c 'import sys,json; d=json.load(sys.stdin); a=d.get("result",{}).get("agent") or d.get("result",{}); print(a["pane_id"])')
  [ -n "$p" ] || { echo "Error: target '$t' does not resolve — herdr agent list" >&2; exit 1; }
  dup=""
  for existing in "${panes[@]+"${panes[@]}"}"; do
    [ "$existing" = "$p" ] && { dup=1; break; }
  done
  if [ -n "$dup" ]; then
    echo "Note: '$t' resolves to an already-targeted pane $p — skipping duplicate." >&2
    continue
  fi
  panes+=("$p"); labels+=("$t")
done

# Preflight: reject panes that are `working` (busy with unrelated prior work)
# or `blocked` (trust/auth dialog — typing into it submits garbage, not a
# task). Matches scripts/broadcast.sh Phase 1b.
ready_panes=(); ready_labels=()
for i in "${!panes[@]}"; do
  st=$(herdr pane get "${panes[$i]}" | python3 -c 'import sys,json; print(json.load(sys.stdin)["result"]["pane"].get("agent_status",""))')
  case "$st" in
    working) echo "Error: '${labels[$i]}' (${panes[$i]}) is already working — skipped." >&2; continue ;;
    blocked) echo "Error: '${labels[$i]}' (${panes[$i]}) is blocked (trust/auth dialog) — skipped." >&2; continue ;;
  esac
  ready_panes+=("${panes[$i]}"); ready_labels+=("${labels[$i]}")
done
panes=("${ready_panes[@]+"${ready_panes[@]}"}"); labels=("${ready_labels[@]+"${ready_labels[@]}"}")
[ "${#panes[@]}" -gt 0 ] || { echo "Error: no targets left to send to." >&2; exit 1; }

tmpdir="$(mktemp -d)"
markers=(); tasks=()
for i in "${!panes[@]}"; do
  herdr pane read "${panes[$i]}" --source recent-unwrapped --lines 80 >"$tmpdir/$i.baseline"
  suffix="$(date +%s)_$$_${i}_$RANDOM"
  markers+=("HERDR_DONE_$suffix")
  tasks[$i]="$msg

After fully finishing, concatenate and print: HERDR_DONE_ and $suffix"
done
for i in "${!panes[@]}"; do
  herdr pane run "${panes[$i]}" "${tasks[$i]}"
done

for i in "${!panes[@]}"; do
  python3 "$here/wait_for_idle.py" "${panes[$i]}" --timeout 180 --lines 80 \
    --baseline-file "$tmpdir/$i.baseline" --completion-marker "${markers[$i]}" &
done
wait
rm -rf "$tmpdir"
```

Do **not** `agent send` and then `pane run` the same message (double submit). Do **not** wait only on `done` for the full budget when the tab is focused — agents often settle as `idle` (use `wait_for_idle.py` or idle|done polling). Do **not** drop the dedupe or busy/blocked preflight from this manual path — that would reintroduce double-sends and dialog-clobbering that `scripts/broadcast.sh` exists to prevent.

## Troubleshooting

| Symptom | Check |
|---|---|
| CLI errors "server not running" | `herdr status`; user starts `herdr` once in a real TTY |
| Sub-agent on a new tab | You used `tab create` — use grid split in the root tab instead |
| Root pane taken by worker | Never `pane run` the worker CLI on `$HERDR_PANE_ID` |
| Unequal-width columns | Always split the current rightmost column and apply the full resize plan from `next_grid_split.py` |
| Agent always `unknown` | `herdr integration install <agent>`; `herdr agent explain <target>` |
| Nested tmux breaks detection | Don't run tmux inside Herdr panes |
| `pane run` typed but agent idle | `herdr pane send-keys $pane enter`; re-wait `working` |
| Status stuck `working` | `pane read`; overall wait budget; escalate stall |
| `blocked` | Human must answer dialog; `agent focus` to show it |
| Panes too narrow | Fewer agents (equal-width columns shrink every time); tab-per-agent only if user asks |
| Wrong project files | Confirm `--cwd` before spawn |
| Name not found | `herdr agent list`; names are unique session-wide |
| Accidentally focused spawn | Pass `--no-focus` on `pane split` / `agent start` |

### Debug one pane

```bash
herdr pane get "$pane_id"
herdr agent explain "$pane_id"
herdr agent explain "$pane_id" --json
herdr pane process-info --pane "$pane_id"
```

### Logs

```
~/.config/herdr/herdr.log
~/.config/herdr/herdr-client.log
~/.config/herdr/herdr-server.log
HERDR_LOG=herdr=debug herdr   # human client only
```

## Mapping from tmux-agent-comms

| tmux | Herdr |
|---|---|
| `tmux split-window` from current | `next_grid_split.py` + `herdr pane split <rightmost> --direction right --no-focus` + `herdr pane resize` on every column |
| session name | agent `name` + `pane_id` |
| `tmux send-keys … Enter` | `herdr pane run` |
| `tmux capture-pane -p -S -40` | `herdr pane read … --source recent-unwrapped --lines 40` |
| `tmux has-session` | `herdr agent get` / `herdr pane get` |
| `tmux kill-pane` (worker) | `herdr pane close` (sub-agent only) |
| `tmux kill-server` | `herdr server stop` (confirm!) |
| multiple app terminal tabs | **one** tab grid: root + tiled sub-agents |
