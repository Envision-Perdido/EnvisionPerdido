#!/bin/bash
# new-branch.sh - Helper script to create new branches with naming conventions
# Usage: ./scripts/new-branch.sh
# Requires: Git installed and in PATH

set -e

BRANCH_TYPE="${1:-}"
BRANCH_NAME="${2:-}"

show_menu() {
    echo ""
    echo "╔════════════════════════════════════════════════════════╗"
    echo "║       Create New Branch - Select Type                  ║"
    echo "╚════════════════════════════════════════════════════════╝"
    echo ""
    echo "  1) feature  - New feature or enhancement"
    echo "  2) fix      - Bug fix or patch"
    echo "  3) refactor - Code cleanup or refactoring"
    echo "  4) perf     - Performance improvement"
    echo "  5) exp      - Experiment or prototype"
    echo ""
}

# Determine type if not provided
if [ -z "$BRANCH_TYPE" ]; then
    while true; do
        show_menu
        read -p "Enter your choice (1-5): " selection
        
        case $selection in
            1) BRANCH_TYPE="feature"; break ;;
            2) BRANCH_TYPE="fix"; break ;;
            3) BRANCH_TYPE="refactor"; break ;;
            4) BRANCH_TYPE="perf"; break ;;
            5) BRANCH_TYPE="exp"; break ;;
            *) echo "Invalid choice. Please try again." >&2 ;;
        esac
    done
fi

# Validate type
if ! echo "$BRANCH_TYPE" | grep -Eq '^(feature|fix|refactor|perf|exp)$'; then
    echo "Error: Invalid branch type '$BRANCH_TYPE'" >&2
    echo "Allowed types: feature, fix, refactor, perf, exp" >&2
    exit 1
fi

# Get branch name if not provided
if [ -z "$BRANCH_NAME" ]; then
    echo ""
    read -p "Enter a short branch name (e.g., 'wordpress-images', 'timezone-bug'): " BRANCH_NAME
fi

# Validate and normalize branch name
BRANCH_NAME=$(echo "$BRANCH_NAME" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | sed 's/[^a-z0-9-]//g')

if [ -z "$BRANCH_NAME" ]; then
    echo "Error: Branch name cannot be empty" >&2
    exit 1
fi

if [ ${#BRANCH_NAME} -gt 40 ]; then
    echo "Warning: Branch name is long (${#BRANCH_NAME} chars). Consider shortening." >&2
fi

FULL_BRANCH_NAME="$BRANCH_TYPE/$BRANCH_NAME"

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║           Creating Branch: $FULL_BRANCH_NAME              ║"
echo "╚════════════════════════════════════════════════════════╝"

# Check if in git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "Error: Not in a Git repository" >&2
    exit 1
fi

echo ""
echo "1️⃣  Checking out 'dev' branch..."
if ! git checkout dev; then
    echo "Error: Could not checkout 'dev' branch" >&2
    exit 1
fi

echo "2️⃣  Pulling latest changes from origin..."
if ! git pull origin dev 2>/dev/null; then
    echo "Warning: Could not pull from origin (may not have network access)" >&2
fi

echo "3️⃣  Creating branch '$FULL_BRANCH_NAME'..."
if ! git checkout -b "$FULL_BRANCH_NAME"; then
    echo "Error: Could not create branch (may already exist)" >&2
    exit 1
fi

echo "4️⃣  Pushing branch to origin..."
if ! git push -u origin "$FULL_BRANCH_NAME" 2>/dev/null; then
    echo "Warning: Could not push to remote (may not have network access)" >&2
fi

echo ""
echo "✅ Branch created successfully!"
echo ""
echo "   Branch name:  $FULL_BRANCH_NAME"
echo "   Base branch:  dev"
echo "   Tracking:     origin/$FULL_BRANCH_NAME"
echo ""
echo "📝 Next steps:"
echo "   1. Make your changes"
echo "   2. Commit: git commit -m '[$BRANCH_TYPE] Your description here'"
echo "   3. Push:   git push origin $FULL_BRANCH_NAME"
echo "   4. Create a Pull Request on GitHub (target: dev)"
echo ""
