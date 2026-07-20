# Documentation decisions

Append-only log of ambiguities resolved while reconciling docs to the code.

## 2026-07-20

- Q: Full doc-manager inventory scope (option C) — include guide, CHANGELOG, historical root MD dumps, and GH Pages HTML?
- A (user): Yes to full inventory including guide + CHANGELOG. Follow-up “fix open items” brought `docs/index.html` into scope; it was reconciled to current catalog counts, versions, tool support, and installable skills.
- Source: user scope replies “C” and “fix open items”

- Q: Root status/checklist files (`APPSTORE_*`, `PHASE_1_SUMMARY.md`, `DEPLOYMENT_CHECKLIST.md`, etc.) — keep, archive, or delete?
- A (user/doc-manager): User asked to fix remaining open items. Preserve the prose by moving drafts into `docs/archive/`, keep root draft filenames ignored to prevent future local dumps, and explicitly unignore the archived copies in `.gitignore`.
- Source: user reply “fix open items”, `.gitignore` (Documentation drafts block), `docs/archive/README.md`

- Q: Should `clean-code` appear in the README skill catalog?
- A (doc-manager): No. `skills/clean-code/` has no `SKILL.md`; CHANGELOG Unreleased states `clean-code` was merged into `code-review` `clean` mode. Catalog lists installable skills only.
- Source: `CHANGELOG.md` (Unreleased / Removed Skills), `skills/clean-code/` listing, `skills/code-review/SKILL.md` frontmatter

- Q: CONTRIBUTING pointed at `python3 skills/skill-creator/scripts/*` — correct path?
- A (doc-manager): Code/config truth is external skill-creator at `~/.claude/skills/skill-creator/scripts/` (`CLAUDE.md:7-9`). There is no `skills/skill-creator` in this repo. CONTRIBUTING updated to match.
- Source: `CLAUDE.md:7-12`, absence of `skills/skill-creator`

- Q: README frontmatter example vs real skills — top-level `version` or `metadata.version`?
- A (doc-manager): Real skills use `metadata.version` (and often `license`, `effort`). README + CONTRIBUTING examples updated to that shape.
- Source: `skills/doc-manager/SKILL.md`, `skills/code-review/SKILL.md`

- Q: Guide line “No README.md inside the skill folder” vs catalog convention of `docs/README.md`?
- A (doc-manager): Repo convention allows human-only `docs/README.md` with AI-skip comment (`CLAUDE.md:20`, CONTRIBUTING). Guide corrected: no root-level skill `README.md`; `docs/README.md` is allowed.
- Source: `CLAUDE.md:20`, existing `skills/*/docs/README.md`
