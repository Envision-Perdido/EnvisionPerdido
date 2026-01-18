# Branching Quick Reference

Copy-paste commands for common Git workflows in this project.

## Create a New Branch

### PowerShell (Windows)
```powershell
# Interactive helper (recommended)
.\scripts\new-branch.ps1

# Manual
git checkout dev
git pull origin dev
git checkout -b feature/my-feature-name
git push -u origin feature/my-feature-name
```

### Bash (macOS/Linux)
```bash
# Interactive helper (recommended)
./scripts/new-branch.sh

# Manual
git checkout dev
git pull origin dev
git checkout -b feature/my-feature-name
git push -u origin feature/my-feature-name
```

## Common Workflow

```bash
# Make changes
echo "your code" > file.py

# Stage and commit (focused commits)
git add file.py
git commit -m "[feature] Add new capability"

# Push frequently
git push origin feature/my-feature-name

# When ready: Create PR on GitHub (base: dev)
# After approval: Merge via GitHub UI
```

## Keep Branch Updated

```bash
# Option 1: Rebase (cleaner history—recommended for feature branches)
git fetch origin
git rebase origin/dev

# Option 2: Merge (preserves history)
git fetch origin
git merge origin/dev

# Push updated branch
git push origin feature/my-feature-name
```

## Resolve Merge Conflicts

```bash
# During rebase: abort and switch to merge
git rebase --abort
git merge origin/dev

# Fix conflicts in your editor, then:
git add .
git commit -m "Resolve merge conflicts with dev"
git push origin feature/my-feature-name
```

## Sync After Merge to Dev

```bash
# If your PR was merged to dev, sync your local dev
git checkout dev
git pull origin dev

# Create a new branch for next work
git checkout -b feature/next-work
```

## Delete Old Branches

```bash
# Clean up local branches not on remote
git fetch --prune

# Delete merged local branches
git branch --merged | grep -v main | grep -v dev | xargs git branch -d
```

## Squash Commits Before Merge (Optional)

If you want to squash your commits before merging to `dev`:

```bash
# Interactive rebase: squash last 3 commits
git rebase -i HEAD~3

# Change 'pick' to 'squash' (or 's') for commits to combine
# Save and close editor
# Force push (only do this on your feature branch!)
git push origin feature/my-feature-name --force
```

## Verify Branch Status

```bash
# Check all branches with tracking info
git branch -vv

# Check what's in your branch vs dev
git log origin/dev..HEAD --oneline

# Check what's in dev but not your branch
git log HEAD..origin/dev --oneline
```

## Release: Merge Dev → Main

```bash
# Update both branches
git checkout dev
git pull origin dev

git checkout main
git pull origin main

# Run tests/health checks
python -m pytest
./scripts/check_evcal_srow.py

# Merge dev into main (no fast-forward recommended)
git merge --no-ff dev
git push origin main

# Optional: tag the release
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0
```

## Emergency: Undo Local Changes

```bash
# Discard changes in a file
git restore file.py

# Discard all uncommitted changes
git restore .

# Unstage a file
git restore --staged file.py

# Undo last commit (keep changes)
git reset --soft HEAD~1

# Undo last commit (discard changes)
git reset --hard HEAD~1
```

## Emergency: Recovery

```bash
# See all your commits (even if branch deleted)
git reflog

# Recover a deleted branch (replace <commit-hash>)
git checkout -b recovered-branch <commit-hash>
```

## View History

```bash
# See last 10 commits on current branch
git log --oneline -10

# See commits on your branch not on dev
git log --oneline dev..HEAD

# See file history
git log --oneline -- file.py

# See what changed in a commit
git show <commit-hash>

# See all branches and where HEAD is pointing
git log --oneline --all --graph --decorate
```

---

**Need more help?** See [CONTRIBUTING.md](CONTRIBUTING.md) for the full workflow guide.
