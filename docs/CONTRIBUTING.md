# Contributing to EnvisionPerdido

Thank you for contributing to the EnvisionPerdido automated community calendar system! This document outlines our branching strategy, workflow, and conventions to keep the project organized and maintainable.

## Branching Strategy

We follow a **scalable trunk-based development workflow** with protected main and integration branches:

### Branch Types & Purposes

| Branch | Purpose | Rules |
|--------|---------|-------|
| **`main`** | Stable, release-ready code | Protected; no direct commits; merged from `dev` only when stable |
| **`dev`** | Integration branch for tested features | Base for all new work; PR reviews required; regularly merged to `main` |
| **`feature/*`** | New features/enhancements | Created from `dev`; short-lived (days/weeks) |
| **`fix/*`** | Bug fixes and patches | Created from `dev`; prioritized for fast merging |
| **`exp/*`** | Experiments & prototyping | Created from `dev`; may be long-lived; don't merge without discussion |
| **`refactor/*`** | Code cleanup & optimization | Created from `dev`; include before/after tests |
| **`perf/*`** | Performance improvements | Created from `dev`; include benchmarks |

### Branch Naming Convention

Use **lowercase with hyphens**, following the pattern:

```
<type>/<short-description>

Examples:
feature/wordpress-image-uploads
fix/event-timezone-parsing
exp/svm-model-optimization
refactor/event-classifier-module
perf/csv-export-streaming
```

## Workflow: Create → Develop → Review → Merge

### 1️⃣ Create a New Branch

**Quick method (recommended):**

```powershell
# Windows PowerShell
./scripts/new-branch.ps1

# Then follow the prompts for type and name
```

**Manual method:**

```bash
# 1. Start from dev, make sure it's fresh
git checkout dev
git pull origin dev

# 2. Create and switch to your feature branch
git checkout -b feature/my-feature-name

# 3. Push upstream to set tracking
git push -u origin feature/my-feature-name
```

### 2️⃣ Develop & Commit

- Make focused, atomic commits with clear messages
- Commit message format: `[type] Description`

```bash
# Examples:
git commit -m "[feature] Add image upload validation"
git commit -m "[fix] Correct timezone offset in CSV export"
git commit -m "[refactor] Extract classifier helper functions"
git commit -m "[perf] Cache vectorizer in memory"
```

- Push frequently to origin to avoid losing work:
  ```bash
  git push origin feature/my-feature-name
  ```

### 3️⃣ Create a Pull Request

1. Go to GitHub: [EnvisionPerdido Pull Requests](https://github.com/mandevautospa/EnvisionPerdido/pulls)
2. Click **"New pull request"**
3. Set:
   - **Base**: `dev` (never `main`)
   - **Compare**: your `feature/...` branch
4. Fill in the PR template (see below)
5. Assign reviewers and request reviews

### 4️⃣ Code Review & Iteration

- Address feedback from reviewers
- Push new commits to the same branch (PR auto-updates)
- Mark conversations as resolved when addressed

```bash
# Make changes based on review
git add .
git commit -m "[review] Address feedback on email formatting"
git push origin feature/my-feature-name
```

### 5️⃣ Merge to `dev`

Once approved:
1. Click **"Squash and merge"** (recommended for cleaner history) or **"Create a merge commit"**
2. Delete the feature branch after merging (GitHub offers this as a button)

### 6️⃣ Merge `dev` → `main` (Release)

When `dev` is stable and ready for production:

```bash
# 1. Update and verify dev is clean
git checkout dev
git pull origin dev

# 2. Verify tests and healthchecks pass
python -m pytest
./scripts/check_evcal_srow.py

# 3. Merge dev into main
git checkout main
git pull origin main
git merge --no-ff dev
git push origin main

# 4. (Optional) Tag the release
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0
```

## Rules of Thumb: When to Branch

**Create a new branch when:**
- ✅ Adding a feature (even small ones)
- ✅ Fixing a bug
- ✅ Refactoring code
- ✅ Experimenting with new ideas
- ✅ Updating documentation

**Do NOT commit directly to:**
- ❌ `main` (ever—it's protected)
- ❌ `dev` (always use a feature/fix branch and PR)

## PR Checklist

Before requesting review, ensure:

- [ ] Branch created from `dev` (not `main`)
- [ ] Commits are focused and well-messaged
- [ ] Code follows project style (see relevant module docs)
- [ ] Tests added or updated (if applicable)
- [ ] No breaking changes without discussion
- [ ] Documentation updated (README, module docstrings, etc.)
- [ ] No environment secrets or credentials in code
- [ ] Merges target `dev` (never `main` directly)

## Development Tips

### Sync with `dev` During Long Development

If you're on a branch for more than a few days, keep it updated:

```bash
# Option 1: Rebase (cleaner history)
git fetch origin
git rebase origin/dev

# Option 2: Merge (preserves history)
git fetch origin
git merge origin/dev

# Push the updated branch
git push origin feature/my-feature-name
```

### Handling Conflicts

If conflicts arise when syncing:

```bash
# During rebase
git rebase --abort  # Cancel and try merge instead
git merge origin/dev

# Resolve conflicts in your editor, then
git add .
git commit -m "Resolve merge conflicts with dev"
git push origin feature/my-feature-name
```

### Cleanup Old Branches

Keep your local repo clean:

```bash
# List branches not on remote
git fetch --prune

# Delete merged local branches
git branch --merged | grep -v main | grep -v dev | xargs git branch -d
```

## GitHub Branch Protection Settings

To enforce this workflow, repository maintainers should enable:

**On `main` branch:**
- ✅ Require pull request reviews before merging
- ✅ Require status checks to pass (tests, health checks)
- ✅ Require branches to be up to date before merging
- ✅ Dismiss stale pull request approvals when new commits are pushed
- ✅ Require code review from code owners (if applicable)
- ✅ Restrict force pushes (allow only admins)

**On `dev` branch:**
- ✅ Require pull request reviews before merging
- ✅ Require status checks to pass
- ⚠️ Force push allowed for maintainers (to clean up history if needed)

See: **Settings** → **Branches** → **Branch protection rules**

## Questions?

Refer to the main [README](README.md) for setup and architecture docs.

For workflow specifics, check:
- [Project Structure](docs/PROJECT_STRUCTURE.md)
- [Quick Reference](docs/QUICK_REFERENCE.md)
- [Windows Setup](docs/WINDOWS_SETUP.md) (if on Windows)
