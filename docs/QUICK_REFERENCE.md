# Quick Reference: Cross-Platform Setup

## TL;DR - Make it Work on Both Mac and Windows

### Windows
```powershell
# One time: create venv & install
python -m venv .venvEnvisionPerdido
.\.venvEnvisionPerdido\Scripts\Activate.ps1
pip install -r requirements.txt

# Edit credentials (your real values)
notepad scripts/windows/env.ps1

# Run pipeline
python scripts/automated_pipeline.py
```

### macOS
```bash
# One time: create venv & install
python3 -m venv .venvEnvisionPerdido
source .venvEnvisionPerdido/bin/activate
pip install -r requirements.txt

# Edit credentials (your real values)
nano scripts/macos/env.sh

# Run pipeline
python scripts/automated_pipeline.py
```

---

## What Changed (Why This Works Now)

### Before
- **Windows**: `env.ps1` loaded by PowerShell `$env:` variables
- **macOS**: You had to manually set credentials in shell
- **VS Code**: Had hardcoded Windows path, broke on Mac
- **Problem**: Switching machines = broken setup

### Now
- **`env_loader.py`**: Auto-detects Windows/macOS and loads right file
- **VS Code Settings**: Uses platform-neutral path `bin/python`
- **Templates**: Both Windows and Mac have templates to copy/edit
- **Priority**: Env vars → local config → secrets folder
- **Result**: `python scripts/automated_pipeline.py` works on ANY machine

---

## File Structure (Important!)

```
scripts/
├── env_loader.py              ← The magic! Auto-loads credentials
├── windows/
│   ├── env.ps1                ← YOUR CREDENTIALS (Windows only, not in git)
│   └── env.ps1.template       ← Template (copy to env.ps1 and edit)
├── macos/
│   ├── env.sh                 ← YOUR CREDENTIALS (macOS only, not in git)
│   └── env.sh.template        ← Template (copy to env.sh and edit)
└── automated_pipeline.py       ← Works on both platforms now!
```

---

## One-Time Setup on New Machine

1. **Clone repo** (or pull if already exists)
2. **Create venv**:
   - Windows: `python -m venv .venvEnvisionPerdido`
   - macOS: `python3 -m venv .venvEnvisionPerdido`
3. **Activate venv**:
   - Windows: `.\.venvEnvisionPerdido\Scripts\Activate.ps1`
   - macOS: `source .venvEnvisionPerdido/bin/activate`
4. **Install deps**: `pip install -r requirements.txt`
5. **Add credentials**:
   - Windows: Edit `scripts/windows/env.ps1`
   - macOS: Edit `scripts/macos/env.sh`
6. **Run**: `python scripts/automated_pipeline.py`

---

## How It Works Behind the Scenes

When you run any script:
```python
from env_loader import load_env
load_env()  # Auto-loaded in all scripts
```

`env_loader.py` does this:
1. Detects your platform (`win32`, `darwin`, `linux`)
2. Looks for `scripts/windows/env.ps1` (Windows) or `scripts/macos/env.sh` (macOS)
3. If not found, checks `~/.secrets/envision_env.ps1` or `.sh`
4. Parses the file and loads into Python's `os.environ`
5. Scripts read credentials from `os.environ`

**Priority order** (first match wins):
1. Already in shell environment
2. Local config file (`scripts/windows/env.ps1` or `scripts/macos/env.sh`)
3. Secrets folder (`~/.secrets/`)

---

## Switching Between Machines

**Mac → Windows:**
- Clone/pull repo on Windows
- Create venv: `python -m venv .venvEnvisionPerdido`
- Install: `pip install -r requirements.txt`
- Add creds to `scripts/windows/env.ps1`
- Run: `python scripts/automated_pipeline.py`
- ✓ Done! No more configuration headaches

**Windows → Mac:**
- Same steps, but use macOS commands
- Edit `scripts/macos/env.sh` instead
- ✓ Done!

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "No module env_loader" | Activate venv first |
| "WP_SITE_URL not found" | Edit `scripts/windows/env.ps1` or `scripts/macos/env.sh` |
| IntelliSense errors in VS Code | Restart VS Code, Cmd/Ctrl+Shift+P → "Python: Clear Cache" |
| API connection fails | Verify credentials in env file, run `python scripts/check_wp_timezone.py` |
| Different behavior on Mac vs Windows | File paths are now platform-agnostic, but check timezone settings if dates look off |

---

## Security Notes

- **NEVER commit** `scripts/windows/env.ps1` or `scripts/macos/env.sh` (both in `.gitignore`)
- **For security**, store credentials in `~/.secrets/` folder instead of repo:
  - Windows: `Copy-Item scripts/windows/env.ps1 ~/.secrets/envision_env.ps1`
  - macOS: `cp scripts/macos/env.sh ~/.secrets/envision_env.sh`
- `env_loader.py` checks `~/.secrets/` first before local folder

---

## Next Steps

1. **Commit these changes** to your `Features` branch
2. **Test on Mac** (or ask another team member)
3. **Update team docs** if needed
4. **Rest easy** — no more OS-specific headaches! 🎉

---

## Files Changed

- ✅ `scripts/env_loader.py` — Now cross-platform
- ✅ `scripts/windows/env.ps1.template` — New
- ✅ `scripts/macos/env.sh` — New
- ✅ `scripts/macos/env.sh.template` — New
- ✅ `.vscode/settings.json` — Platform-agnostic path
- ✅ `.gitignore` — Added credential files
- ✅ `docs/CROSS_PLATFORM_SETUP.md` — Comprehensive guide
- ✅ `docs/QUICK_REFERENCE.md` — This file

All scripts that use credentials already call `load_env()` automatically!
