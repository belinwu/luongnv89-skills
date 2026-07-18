# Herdr recipes for agent fleets

Read this when you need layout variants, multi-line sends, human steer/focus, scrollback recovery, or troubleshooting.

## Default fleet layout (this skill)

**Root + sub-agents as a tiled grid in one tab (vertical panel first):**

```
Session (default)
└── Workspace: <project>
    └── Tab: <root's tab>                 ← single grid view
        ┌───────────────────────────┐
        │ root (you)                │
        ├─────────────┬─────────────┤
        │ reviewer    │ tests       │
        └─────────────┴─────────────┘
```

Why this default: the human sees the **root agent and every sub-agent together at usable sizes**; the orchestrator is never displaced into a side tab; sidebar still rolls status per workspace.

### Spawn N sub-agents into a balanced grid

Use `scripts/next_grid_split.py` before every split: it picks the **largest pane** (tie-break root) and a direction from that pane's aspect ratio.

```bash
root_pane="${HERDR_PANE_ID:?}"
root_tab="${HERDR_TAB_ID:?}"
ws="${HERDR_WORKSPACE_ID:?}"
project_dir=$(pwd)
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"  # when run from scripts/
# or: here=skills/herdr-agent-comms/scripts

spawn_sub() {
  local name=$1 cmd=$2
  local split_from dir j pane
  herdr agent list | grep -q "\"name\":\"$name\"" && name="${name}-$(date +%s)"
  read -r split_from dir < <(python3 "$here/next_grid_split.py" --root-pane "$root_pane")
  j=$(herdr pane split "$split_from" --direction "$dir" --cwd "$project_dir" --no-focus)
  pane=$(printf '%s' "$j" | python3 -c 'import sys,json; d=json.load(sys.stdin); r=d["result"]; print((r.get("pane") or r)["pane_id"])')
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
| Target pane | largest area in the tab (`width * height`) |
| Tie-break | prefer root pane |
| Direction | **`down` if target height ≥ width** (vertical first), else `right` |
| After each spawn | re-run the chooser — never hardcode a fixed dir sequence |
| Focus | always `--no-focus` |

```bash
python3 scripts/next_grid_split.py --root-pane "$root_pane"
herdr pane layout --pane "$root_pane"   # verify balanced rects
```

Manual fallback without the helper: read `herdr pane layout`, pick the largest `rect`, split that pane with the aspect rule above.

### Prefer grid split over `agent start`

| Command | When |
|---|---|
| `next_grid_split.py` + `herdr pane split … --no-focus` | **Default** — balanced grid including root |
| `herdr agent start name --tab "$root_tab" --split right --no-focus -- …` | OK if you only care about same tab; may create slivers |

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
read -r split_from dir < <(python3 scripts/next_grid_split.py --root-pane "$root_pane")
j=$(herdr pane split "$split_from" --direction "$dir" --cwd "$project_dir" --no-focus)
pane=$(printf '%s' "$j" | python3 -c 'import sys,json; d=json.load(sys.stdin); r=d["result"]; print((r.get("pane") or r)["pane_id"])')
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

Prefer `scripts/broadcast.sh`. Manual equivalent:

```bash
targets=(reviewer tests docs)
msg="Pull latest main and report branch + dirty state."

# Resolve names → pane ids once, then single pane run each
panes=()
for t in "${targets[@]}"; do
  p=$(herdr agent get "$t" | python3 -c 'import sys,json; d=json.load(sys.stdin); a=d.get("result",{}).get("agent") or d.get("result",{}); print(a["pane_id"])')
  panes+=("$p")
done

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
  python3 scripts/wait_for_idle.py "${panes[$i]}" --timeout 180 --lines 80 \
    --baseline-file "$tmpdir/$i.baseline" --completion-marker "${markers[$i]}" &
done
wait
rm -rf "$tmpdir"
```

Do **not** `agent send` and then `pane run` the same message (double submit). Do **not** wait only on `done` for the full budget when the tab is focused — agents often settle as `idle` (use `wait_for_idle.py` or idle|done polling).

## Troubleshooting

| Symptom | Check |
|---|---|
| CLI errors "server not running" | `herdr status`; user starts `herdr` once in a real TTY |
| Sub-agent on a new tab | You used `tab create` — use grid split in the root tab instead |
| Root pane taken by worker | Never `pane run` the worker CLI on `$HERDR_PANE_ID` |
| Thin sliver panes | Always split the largest pane via `next_grid_split.py` |
| Agent always `unknown` | `herdr integration install <agent>`; `herdr agent explain <target>` |
| Nested tmux breaks detection | Don't run tmux inside Herdr panes |
| `pane run` typed but agent idle | `herdr pane send-keys $pane enter`; re-wait `working` |
| Status stuck `working` | `pane read`; overall wait budget; escalate stall |
| `blocked` | Human must answer dialog; `agent focus` to show it |
| Panes too narrow | Fewer agents; rebalance by largest-pane splits; tab-per-agent only if user asks |
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
| `tmux split-window` from current | `next_grid_split.py` + `herdr pane split <largest> --direction right\|down --no-focus` |
| session name | agent `name` + `pane_id` |
| `tmux send-keys … Enter` | `herdr pane run` |
| `tmux capture-pane -p -S -40` | `herdr pane read … --source recent-unwrapped --lines 40` |
| `tmux has-session` | `herdr agent get` / `herdr pane get` |
| `tmux kill-pane` (worker) | `herdr pane close` (sub-agent only) |
| `tmux kill-server` | `herdr server stop` (confirm!) |
| multiple app terminal tabs | **one** tab grid: root + tiled sub-agents |
