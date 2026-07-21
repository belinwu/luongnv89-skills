# Command checks

Use these commands after selecting a path; replace placeholders before running them.

## Routine sync

```bash
git fetch upstream
git fetch origin
git checkout <feature-branch>
git rebase upstream/<default-branch>
git push origin <feature-branch> --force-with-lease
git checkout <default-branch>
git reset --hard upstream/<default-branch>
git merge --ff-only <feature-branch>
git push origin <default-branch> --force-with-lease
```

If `--ff-only` fails, do not push. Rebase the feature branch against the current upstream tip, verify it, then retry.

## Equality and ancestry

```bash
git rev-parse upstream/<default-branch>
git rev-parse <default-branch>
git rev-parse <feature-branch>
git merge-base --is-ancestor upstream/<default-branch> <default-branch>
git rev-list --count upstream/<default-branch>..<default-branch>
git status --short
```

Path C requires the default branch and feature branch SHAs to match. Path D requires the default branch and upstream SHAs to match. An empty `git status --short` confirms no unresolved working-tree changes.
