# Contributing to Agent Skills

Thank you for your interest in contributing. This document is the setup and process runbook for this repository.

> Validate this runbook: `./scripts/validate-contribute.sh --check`

## How to Contribute

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/my-new-skill`) — this repo uses `feat/` prefixes (`git branch -r`)
3. Make your changes
4. Commit using conventional commits (`git commit -m "feat: add new skill"`)
5. Push to your branch (`git push origin feat/my-new-skill`)
6. Open a Pull Request

## Development Setup

This repo has **no** `npm`, `pnpm`, `make`, or `pytest` (`CLAUDE.md:12`). Skills are Markdown + optional scripts. Scaffold/validate tooling lives in the external **skill-creator** skill, not under `skills/` in this tree.

Prerequisites:

- `git` ≥ 2.30
- `python3` on `PATH`
- `skill-creator` installed for your agent so these scripts resolve:
  - `~/.claude/skills/skill-creator/scripts/init_skill.py`
  - `~/.claude/skills/skill-creator/scripts/package_skill.py`
  - `~/.claude/skills/skill-creator/scripts/quick_validate.py`
  (`CLAUDE.md:7-9`)

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/skills.git
cd skills

# Scaffold a new skill (writes under skills/)
python3 ~/.claude/skills/skill-creator/scripts/init_skill.py my-skill --path skills/

# Edit the skill
# ... make changes to skills/my-skill/SKILL.md

# Validate (preferred during development)
python3 ~/.claude/skills/skill-creator/scripts/quick_validate.py skills/my-skill

# Package (produces a bundle under dist/ — do not hand-edit dist/)
python3 ~/.claude/skills/skill-creator/scripts/package_skill.py skills/my-skill
```

Local installer dry-run (interactive TUI; needs a TTY) (`CLAUDE.md:10`, `install.sh`):

```bash
bash install.sh
```

Non-interactive remote install options are documented in `remote-install.sh:11-13` and [README.md](README.md#install).

## Skill Structure

Each skill must follow this structure (`CLAUDE.md:16-20`, `CONTRIBUTING` layout used by existing skills):

```
skill-name/
├── SKILL.md              # Required: skill definition
├── docs/                 # Optional: human-only docs, never auto-loaded
│   └── README.md         # Optional: catalog-browsing docs (AI-skip notice at top)
├── references/           # Optional: docs the agent loads on demand
├── scripts/              # Optional: executable scripts
├── agents/               # Optional: subagent prompts
└── assets/               # Optional: templates and resources
```

If a skill ships a `README.md`, place it under `docs/` (not at the skill root and not under `references/`) and start it with the AI-skip HTML comment. The runtime loader reads `SKILL.md` + `references/` + `scripts/` + `agents/` when a skill triggers; `docs/` sits outside that set, so a README parked there costs zero runtime tokens (`CLAUDE.md:20`).

**Suite folders.** Multi-phase products use an umbrella at `skills/<umbrella>/` plus children at `skills/<umbrella>/<child>/` (e.g. `website-cloner`, `diagram-generator`). Installers discover both levels (`install.sh:44-46`). Each `SKILL.md` — umbrella and child — has `name` equal to **its own** directory name and its own `metadata.version`.

### SKILL.md Requirements

Real skills in this repo use this frontmatter shape (example pattern from `skills/doc-manager/SKILL.md`, `skills/code-review/SKILL.md`):

```yaml
---
name: skill-name
description: "What it does and when to use it. Don't use for X."
license: MIT
effort: medium
metadata:
  version: 1.0.0
  author: "Your Name"
---

# Skill content...
```

Hard rules for this catalog (`CLAUDE.md:28-42`):

1. Bump `metadata.version` (semver) on every `SKILL.md` edit.
2. Quote frontmatter strings containing `:` `#` `-` `<` `>` `|` `,` `&` `?` `!`.
3. Keep each `SKILL.md` under 500 lines; spill to `references/`.
4. `name` must exactly match the parent directory name (lowercase, hyphens).
5. Start every `docs/README.md` with the AI-skip HTML comment (see existing skills).
6. Never hand-edit `dist/`; regenerate via `package_skill.py`.
7. Do not commit `*-workspace/` contents or secrets.
8. Run `quick_validate.py` on any skill you touched before opening a PR.

## Commit Message Convention

We use [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` New feature or skill
- `fix:` Bug fix
- `docs:` Documentation changes
- `refactor:` Code refactoring
- `test:` Adding or updating tests
- `chore:` Maintenance tasks

Examples:

- `feat: add code-review skill`
- `fix: correct trigger phrases in auto-push`
- `docs: update installation instructions`

## Versioning

Skills use [semantic versioning](https://semver.org/) (`MAJOR.MINOR.PATCH`) in `metadata.version`:

- **PATCH** (e.g., `1.0.0` → `1.0.1`): Bug fixes, typo corrections
- **MINOR** (e.g., `1.0.0` → `1.1.0`): New features, added capabilities
- **MAJOR** (e.g., `1.0.0` → `2.0.0`): Breaking changes to skill behavior

Always update `metadata.version` in `SKILL.md` when modifying a skill (`CLAUDE.md:28`). Also update the version cell in the root [README.md](README.md) skill catalog.

## Pull Request Process

1. Ensure your skill passes validation (`quick_validate.py`)
2. Update [README.md](README.md) if adding a new skill (catalog row + version)
3. Add an entry under `## Unreleased` in [CHANGELOG.md](CHANGELOG.md)
4. Fill out the PR template completely (`.github/PULL_REQUEST_TEMPLATE.md`)
5. Wait for review and address any feedback

## Code of Conduct

Please read our [Code of Conduct](CODE_OF_CONDUCT.md) before contributing.

## Questions?

Open an issue for any questions about contributing.
