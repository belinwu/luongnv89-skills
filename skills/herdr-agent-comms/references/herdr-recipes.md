# Herdr recipes for agent fleets

Read this when you need layout variants, multi-line sends, human steer/focus, scrollback recovery, or troubleshooting.

## Default fleet layout (this skill)

**Root agent pane + sub-agents split from root — one tab:**

```
Session (default)
└── Workspace: <project>
    └── Tab: <root's tab>                 ← single view
        ├── pane root   agent "orchestrator" / caller  ($HERDR_PANE_ID)
        ├── pane right  agent "reviewer"               (split from root)
        └── pane down   agent "tests"                  (split from root)
```

Why this default: the human sees the **root agent and every sub-agent together**; the orchestrator is never displaced into a side tab; sidebar still rolls status per workspace.

### Spawn N sub-agents from the root pane

```bash
root_pane="${HERDR_PANE_ID:?}"
root_tab="${HERDR_TAB_ID:?}"
ws="${HERDR_WORKSPACE_ID:?}"
project_dir=$(pwd)

spawn_sub() {
  local name=$1 dir=$2 cmd=$3
  local j pane
  herdr agent list | grep -q "\"name\":\"$name\"" && name="${name}-$(date +%s)"
  j=$(herdr pane split "$root_pane" --direction "$dir" --cwd "$project_dir" --no-focus)
  pane=$(printf '%s' "$j" | python3 -c 'import sys,json; d=json.load(sys.stdin); r=d["result"]; print((r.get("pane") or r)["pane_id"])')
  herdr pane rename "$pane" "$name"
  herdr agent rename "$pane" "$name"
  herdr pane run "$pane" "$cmd"
  printf '%s\n' "$pane"
}

p_reviewer=$(spawn_sub reviewer right "pi --thinking medium")
p_tests=$(spawn_sub tests down "pi --thinking low")
# optional third: spawn_sub docs right "pi --thinking low"
```

### Split direction heuristics

| Situation | Direction |
|---|---|
| First sub-agent | `right` |
| Second sub-agent | `down` |
| Wide source pane | prefer `right` |
| Tall/narrow source pane | prefer `down` |
| Unknown geometry | alternate `right`, `down`, `right`, … |

```bash
herdr pane layout --pane "$root_pane"
```

Always pass **`--no-focus`** so the root agent keeps the keyboard while the fleet builds.

### Prefer `pane split` over `agent start` for anchoring

| Command | When |
|---|---|
| `herdr pane split "$root_pane" --direction … --no-focus` | **Default** — split is guaranteed off the root pane |
| `herdr agent start name --tab "$root_tab" --split right --no-focus -- …` | OK if you only care about same tab; may split relative to last focused pane |

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

### Adding a log / shell pane beside the root

```bash
j=$(herdr pane split "$root_pane" --direction down --cwd "$project_dir" --no-focus)
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

for pane in "${panes[@]}"; do
  herdr pane run "$pane" "$msg"
done

for pane in "${panes[@]}"; do
  python3 scripts/wait_for_idle.py "$pane" --timeout 180 &
done
wait
```

Do **not** `agent send` and then `pane run` the same message (double submit). Do **not** wait only on `done` for the full budget when the tab is focused — agents often settle as `idle` (use `wait_for_idle.py` or idle|done polling).

## Troubleshooting

| Symptom | Check |
|---|---|
| CLI errors "server not running" | `herdr status`; user starts `herdr` once in a real TTY |
| Sub-agent on a new tab | You used `tab create` — use `pane split "$root_pane"` instead |
| Root pane taken by worker | Never `pane run` the worker CLI on `$HERDR_PANE_ID` |
| Agent always `unknown` | `herdr integration install <agent>`; `herdr agent explain <target>` |
| Nested tmux breaks detection | Don't run tmux inside Herdr panes |
| `pane run` typed but agent idle | `herdr pane send-keys $pane enter`; re-wait `working` |
| Status stuck `working` | `pane read`; overall wait budget; escalate stall |
| `blocked` | Human must answer dialog; `agent focus` to show it |
| Panes too narrow | Fewer agents; alternate split directions; tab-per-agent only if user asks |
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
| `tmux split-window` from current | `herdr pane split "$root_pane" --direction right\|down --no-focus` |
| session name | agent `name` + `pane_id` |
| `tmux send-keys … Enter` | `herdr pane run` |
| `tmux capture-pane -p -S -40` | `herdr pane read … --source recent-unwrapped --lines 40` |
| `tmux has-session` | `herdr agent get` / `herdr pane get` |
| `tmux kill-pane` (worker) | `herdr pane close` (sub-agent only) |
| `tmux kill-server` | `herdr server stop` (confirm!) |
| multiple app terminal tabs | **one** tab: root + split sub-agents |
