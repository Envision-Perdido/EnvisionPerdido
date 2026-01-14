# new-branch.ps1 - Helper script to create new branches with naming conventions
# Usage: .\scripts\new-branch.ps1
# Requires: Git installed and in PATH

param(
    [string]$Type,
    [string]$Name
)

function Show-Menu {
    Write-Host "`n╔════════════════════════════════════════════════════════╗"
    Write-Host "║       Create New Branch - Select Type                  ║"
    Write-Host "╚════════════════════════════════════════════════════════╝"
    Write-Host ""
    Write-Host "  1) feature  - New feature or enhancement"
    Write-Host "  2) fix      - Bug fix or patch"
    Write-Host "  3) refactor - Code cleanup or refactoring"
    Write-Host "  4) perf     - Performance improvement"
    Write-Host "  5) exp      - Experiment or prototype"
    Write-Host ""
}

# Determine type if not provided
if (-not $Type) {
    while ($true) {
        Show-Menu
        $selection = Read-Host "Enter your choice (1-5)"
        
        switch ($selection) {
            "1" { $Type = "feature"; break }
            "2" { $Type = "fix"; break }
            "3" { $Type = "refactor"; break }
            "4" { $Type = "perf"; break }
            "5" { $Type = "exp"; break }
            default { Write-Host "Invalid choice. Please try again." -ForegroundColor Red }
        }
    }
}

# Validate type
if ($Type -notmatch '^(feature|fix|refactor|perf|exp)$') {
    Write-Host "Error: Invalid branch type '$Type'" -ForegroundColor Red
    Write-Host "Allowed types: feature, fix, refactor, perf, exp" -ForegroundColor Yellow
    exit 1
}

# Get branch name if not provided
if (-not $Name) {
    Write-Host ""
    $Name = Read-Host "Enter a short branch name (e.g., 'wordpress-images', 'timezone-bug')"
}

# Validate branch name
$Name = $Name.Trim().ToLower() -replace '\s+', '-' -replace '[^a-z0-9\-]', ''

if ([string]::IsNullOrWhiteSpace($Name)) {
    Write-Host "Error: Branch name cannot be empty" -ForegroundColor Red
    exit 1
}

if ($Name.Length -gt 40) {
    Write-Host "Warning: Branch name is long (${$Name.Length} chars). Consider shortening." -ForegroundColor Yellow
}

$BranchName = "$Type/$Name"

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════╗"
Write-Host "║           Creating Branch: $BranchName                  ║"
Write-Host "╚════════════════════════════════════════════════════════╝"

# Check if on git repository
try {
    git rev-parse --git-dir | Out-Null
} catch {
    Write-Host "Error: Not in a Git repository" -ForegroundColor Red
    exit 1
}

# Get current branch
$CurrentBranch = git rev-parse --abbrev-ref HEAD

Write-Host ""
Write-Host "1️⃣  Checking out 'dev' branch..." -ForegroundColor Cyan
git checkout dev
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Could not checkout 'dev' branch" -ForegroundColor Red
    exit 1
}

Write-Host "2️⃣  Pulling latest changes from origin..." -ForegroundColor Cyan
git pull origin dev
if ($LASTEXITCODE -ne 0) {
    Write-Host "Warning: Could not pull from origin (may not have network access)" -ForegroundColor Yellow
}

Write-Host "3️⃣  Creating branch '$BranchName'..." -ForegroundColor Cyan
git checkout -b "$BranchName"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Could not create branch (may already exist)" -ForegroundColor Red
    exit 1
}

Write-Host "4️⃣  Pushing branch to origin..." -ForegroundColor Cyan
git push -u origin "$BranchName"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Warning: Could not push to remote (may not have network access)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "✅ Branch created successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "   Branch name:  $BranchName" -ForegroundColor Green
Write-Host "   Base branch:  dev" -ForegroundColor Green
Write-Host "   Tracking:     origin/$BranchName" -ForegroundColor Green
Write-Host ""
Write-Host "📝 Next steps:" -ForegroundColor Cyan
Write-Host "   1. Make your changes"
Write-Host "   2. Commit: git commit -m '[${Type}] Your description here'"
Write-Host "   3. Push:   git push origin $BranchName"
Write-Host "   4. Create a Pull Request on GitHub (target: dev)"
Write-Host ""
