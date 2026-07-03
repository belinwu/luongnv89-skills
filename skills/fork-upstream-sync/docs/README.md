<!--
  DO NOT READ THIS FILE — This README.md is for human catalog browsing only.
  It ships inside the .skill package but is NEVER auto-loaded into agent context.
  The runtime loader only reads SKILL.md + references/ + scripts/ + agents/ when the skill triggers.
  If you're an AI agent, read the SKILL.md file instead for skill instructions.
-->

# Fork Upstream Sync

> Keep your GitHub fork `main` aligned with upstream while your open PR and unmerged work stay on top.

## Highlights

- Adds and uses an `upstream` remote (parent repo), separate from fork `origin`
- Rebases feature branches so upstream PRs show MERGEABLE again
- Builds integration main: `upstream/main` plus your commits (linear history)
- Post-merge path to reset fork `main` to pure upstream

## When to use

- Sync my fork with upstream
- PR has merge conflicts with main
- Fork main up to date but keep not-yet-merged feature

## Author

Luong NGUYEN — luongnv89@gmail.com