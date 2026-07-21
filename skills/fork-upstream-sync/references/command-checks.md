# Command checks

Use only the sequence for the path the user approved. Replace every placeholder before running a command.

## Path B only — repair the PR branch

Use this sequence when the request is only to repair a conflicting PR. It stops after updating and verifying the feature branch.

```bash
git fetch upstream
git fetch origin
git checkout <feature-branch>
git rebase upstream/<default-branch>
git push origin <feature-branch> --force-with-lease
gh pr view <pr-number> --repo <owner>/<repo> --json mergeable,mergeStateStatus
```

**Do not run Path C commands for a Path B-only request.** In particular, do not check out, reset, or push the default branch unless the user separately approves Path C or an explicit combined B+C operation.

Path B is complete when the rebase succeeds, the feature branch is lease-protected on `origin`, and the PR is mergeable (or a CI delay is reported as partial).

## Path C only — approved integration-main rebuild

Run this sequence only when the user explicitly approved rebuilding the fork's integration default branch and the feature branch is already rebased on the current upstream tip:

```bash
git fetch upstream
git fetch origin
git checkout <default-branch>
git reset --hard upstream/<default-branch>
git merge --ff-only <feature-branch>
git push origin <default-branch> --force-with-lease
```

If `--ff-only` fails, do not push. Re-run Path B against the current upstream tip, verify the feature branch, then retry Path C only if its approval still applies.

## Explicit combined Path B+C

Use the combined sequence only when the user asked both to repair the PR branch and to rebuild integration main:

```bash
git fetch upstream
git fetch origin
git checkout <feature-branch>
git rebase upstream/<default-branch>
git push origin <feature-branch> --force-with-lease
gh pr view <pr-number> --repo <owner>/<repo> --json mergeable,mergeStateStatus
git checkout <default-branch>
git reset --hard upstream/<default-branch>
git merge --ff-only <feature-branch>
git push origin <default-branch> --force-with-lease
```

If the fast-forward merge fails, do not push the default branch.

## Path D — approved post-merge cleanup

Use this only after verifying that upstream contains the merged PR and the user asked to make the fork default branch identical to upstream:

```bash
git fetch upstream
git fetch origin
git checkout <default-branch>
git reset --hard upstream/<default-branch>
git push origin <default-branch> --force-with-lease
```

## Path-specific verification

### Path B

```bash
git rev-parse upstream/<default-branch>
git rev-parse <feature-branch>
git merge-base --is-ancestor upstream/<default-branch> <feature-branch>
git status --short
gh pr view <pr-number> --repo <owner>/<repo> --json mergeable,mergeStateStatus
```

### Path C or explicit B+C

```bash
git rev-parse upstream/<default-branch>
git rev-parse <default-branch>
git rev-parse <feature-branch>
git merge-base --is-ancestor upstream/<default-branch> <default-branch>
test "$(git rev-parse <default-branch>)" = "$(git rev-parse <feature-branch>)"
git rev-list --count upstream/<default-branch>..<default-branch>
git status --short
```

### Path D

```bash
git rev-parse upstream/<default-branch>
git rev-parse <default-branch>
test "$(git rev-parse <default-branch>)" = "$(git rev-parse upstream/<default-branch>)"
git status --short
```

An empty `git status --short` confirms no unresolved working-tree changes. Path C requires the default and feature branch SHAs to match; Path D requires the default and upstream SHAs to match.
