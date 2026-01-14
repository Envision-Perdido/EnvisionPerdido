# Cross-Platform Setup Guide

This guide covers setup for both **Windows** and **macOS/Linux** so you can work seamlessly on either platform without configuration headaches.

## Quick Start

### Windows
```powershell
# 1. Clone/navigate to repo
cd c:\Users\scott\UWF-Code\EnvisionPerdido

# 2. Create virtual environment
python -m venv .venvEnvisionPerdido

# 3. Activate it
.\.venvEnvisionPerdido\Scripts\Activate.ps1

# 4. Install dependencies
pip install -r requirements.txt

# 5. Set credentials (edit this file with your real values)
# scripts/windows/env.ps1

# 6. Run pipeline
python scripts/automated_pipeline.py
```

### macOS/Linux
```bash
# 1. Clone/navigate to repo
cd ~/path/to/EnvisionPerdido

# 2. Create virtual environment
python3 -m venv .venvEnvisionPerdido

# 3. Activate it
source .venvEnvisionPerdido/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Set credentials (edit this file with your real values)
# scripts/macos/env.sh

# 6. Run pipeline
python scripts/automated_pipeline.py
```

---

## Detailed Setup

### 1. Virtual Environment

**Windows:**
```powershell
python -m venv .venvEnvisionPerdido
.\.venvEnvisionPerdido\Scripts\Activate.ps1
```

**macOS/Linux:**
```bash
python3 -m venv .venvEnvisionPerdido
source .venvEnvisionPerdido/bin/activate
```

The venv directory is in `.gitignore` — each machine creates its own.

### 2. Install Dependencies

Both platforms:
```bash
pip install -r requirements.txt
```

This installs: pandas, requests, beautifulsoup4, icalendar, scikit-learn, joblib, pytz, pytest, etc.

### 3. Configure Environment Variables

#### **Windows Setup**

1. **Edit credentials file:**
   ```powershell
   code scripts/windows/env.ps1
   ```

2. **Add your credentials** (replace `your_*` placeholders):
   ```powershell
   $env:WP_SITE_URL = "https://your-site.org"
   $env:WP_USERNAME = "your_username"
   $env:WP_APP_PASSWORD = "xxxx xxxx xxxx xxxx"
   $env:SMTP_SERVER = "smtp.gmail.com"
   $env:SMTP_PORT = "587"
   $env:SENDER_EMAIL = "your@gmail.com"
   $env:EMAIL_PASSWORD = "your_app_password"
   $env:RECIPIENT_EMAIL = "notify@gmail.com"
   $env:AUTO_UPLOAD = "false"
   $env:SITE_TIMEZONE = "America/Chicago"
   ```

3. **For extra security**, copy to `~/.secrets/envision_env.ps1` (won't be in git):
   ```powershell
   Copy-Item scripts/windows/env.ps1 ~/.secrets/envision_env.ps1
   ```

#### **macOS/Linux Setup**

1. **Edit credentials file:**
   ```bash
   nano scripts/macos/env.sh
   # or
   code scripts/macos/env.sh
   ```

2. **Add your credentials:**
   ```bash
   export WP_SITE_URL="https://your-site.org"
   export WP_USERNAME="your_username"
   export WP_APP_PASSWORD="xxxx xxxx xxxx xxxx"
   export SMTP_SERVER="smtp.gmail.com"
   export SMTP_PORT="587"
   export SENDER_EMAIL="your@gmail.com"
   export EMAIL_PASSWORD="your_app_password"
   export RECIPIENT_EMAIL="notify@gmail.com"
   export AUTO_UPLOAD="false"
   export SITE_TIMEZONE="America/Chicago"
   ```

3. **For extra security**, copy to `~/.secrets/envision_env.sh`:
   ```bash
   mkdir -p ~/.secrets
   cp scripts/macos/env.sh ~/.secrets/envision_env.sh
   chmod 600 ~/.secrets/envision_env.sh
   ```

### 4. Environment Loading in Python

All Python scripts automatically load credentials via `env_loader.py`:

```python
from env_loader import load_env
load_env()

# Now os.environ has all your credentials
site_url = os.environ.get("WP_SITE_URL")
```

**Loading priority** (first one found wins):
1. Already set in shell/terminal
2. `scripts/windows/env.ps1` (Windows) or `scripts/macos/env.sh` (macOS)
3. `~/.secrets/envision_env.ps1` or `~/.secrets/envision_env.sh`

---

## VS Code Configuration

The `.vscode/settings.json` file is **platform-aware**:

```json
"python.defaultInterpreterPath": "${workspaceFolder}/.venvEnvisionPerdido/bin/python"
```

- **Windows**: VS Code finds `Scripts/python.exe` via the `bin` symlink
- **macOS/Linux**: Uses `/bin/python` directly

**If you see IntelliSense errors:**
1. Press `Ctrl+Shift+P` (Cmd+Shift+P on Mac)
2. Search "Python: Select Interpreter"
3. Choose `.venvEnvisionPerdido`
4. Press `Ctrl+Shift+P` → "Python: Clear Cache"

---

## Running the Pipeline

**Any platform:**
```bash
# Activate venv first
# Windows: .\.venvEnvisionPerdido\Scripts\Activate.ps1
# macOS:   source .venvEnvisionPerdido/bin/activate

# Run pipeline
python scripts/automated_pipeline.py
```

**Expected output:**
```
✓ Loaded 9 environment variables from scripts/windows/env.ps1
Scraping events...
Classifying events...
Exporting to CSV...
Sending email notification...
```

---

## Troubleshooting

### "No module named 'env_loader'"
- **Windows**: Ensure you're in the venv: `.\.venvEnvisionPerdido\Scripts\Activate.ps1`
- **macOS**: Ensure you're in the venv: `source .venvEnvisionPerdido/bin/activate`
- Verify `scripts/env_loader.py` exists

### "WP_SITE_URL not found in environment"
- **Windows**: Edit `scripts/windows/env.ps1` with your credentials
- **macOS**: Edit `scripts/macos/env.sh` with your credentials
- Alternatively, set in terminal: `$env:WP_SITE_URL = "..."` (Windows) or `export WP_SITE_URL="..."` (macOS)

### "API connection failed"
- Verify WordPress URL is correct and accessible
- Verify app password is valid (not expired)
- Test with: `python scripts/check_wp_timezone.py`

### Python interpreter not found
- Run `python -m venv .venvEnvisionPerdido` again
- Make sure Python 3.8+ is installed: `python --version`

### IntelliSense shows false errors
- Restart VS Code
- Press `Ctrl+Shift+P` → "Python: Clear Cache"
- Select interpreter again from dropdown

---

## File Structure

```
EnvisionPerdido/
├── .venvEnvisionPerdido/      ← Your venv (don't commit)
├── .vscode/
│   └── settings.json          ← Platform-aware interpreter path
├── scripts/
│   ├── env_loader.py          ← Auto-loads credentials
│   ├── windows/
│   │   └── env.ps1            ← Windows credentials (EDIT THIS)
│   ├── macos/
│   │   └── env.sh             ← macOS credentials (EDIT THIS)
│   ├── automated_pipeline.py
│   ├── wordpress_uploader.py
│   └── ...
├── requirements.txt
└── ...
```

---

## Next Steps

1. **Update credentials** in your platform's env file (`env.ps1` or `env.sh`)
2. **Activate venv** and install dependencies
3. **Test API connection**: `python scripts/check_wp_timezone.py`
4. **Run pipeline**: `python scripts/automated_pipeline.py`

For automation on Windows, see: [WINDOWS_SETUP.md](./WINDOWS_SETUP.md)  
For automation on macOS, see: [MACOS_SETUP.md](./MACOS_SETUP.md) (coming soon)

---

## Support

If you switch machines:
1. Clone repo on new machine
2. Create venv: `python -m venv .venvEnvisionPerdido`
3. Install deps: `pip install -r requirements.txt`
4. Add credentials: `scripts/windows/env.ps1` or `scripts/macos/env.sh`
5. Run: `python scripts/automated_pipeline.py`

That's it! `env_loader.py` handles the rest automatically.
