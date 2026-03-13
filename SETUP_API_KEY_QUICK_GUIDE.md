# How to Use Environment Variables (Step-by-Step)

## Your Setup (Already in Place!)

Your code is **already configured** to load environment variables from:
```
C:\Users\scott\UWF-Code\EnvisionPerdido\scripts\windows\env.ps1
```

This file is in `.gitignore` so it will NEVER be committed to GitHub.

---

## How to Add API Keys

### Step 1: Edit env.ps1 (After Revoking Old Key)

1. **Revoke your old key first:**
   - Go to: https://platform.openai.com/api-keys
   - Delete the key starting with `sk-proj-HP6-dwItA2J0Q...`

2. **Generate a new key:**
   - On same page, click "Create new secret key"
   - Copy it (only shows once!)

3. **Edit this file in VS Code:**
   ```
   C:\Users\scott\UWF-Code\EnvisionPerdido\scripts\windows\env.ps1
   ```

4. **Find this section and add your new key:**
   ```powershell
   # OpenAI Configuration
   $env:OPENAI_API_KEY = "sk-proj-your-new-key-here"
   ```

5. **Save the file** (Ctrl+S)

### Step 2: Load the Environment

Every time you run the pipeline, PowerShell loads the variables:

```powershell
# Method 1: Run via run_pipeline.ps1 (it auto-loads)
cd C:\Users\scott\UWF-Code\EnvisionPerdido
.\scripts\windows\run_pipeline.ps1

# Method 2: Manual load + run
& .\scripts\windows\env.ps1
python scripts/automated_pipeline.py
```

### Step 3: Verify It Works

```powershell
# Activate venv
& .\.venvEnvisionPerdido\Scripts\Activate.ps1

# Load env
& .\scripts\windows\env.ps1

# Test the key is loaded
python -c "import os; key = os.getenv('OPENAI_API_KEY'); print('✓ Key found!' if key and key.startswith('sk-proj-') else '✗ Key not found')"
```

---

## How Your Code Uses It

Your Python code does this automatically:

```python
# In scripts/automated_pipeline.py (line 40)
from env_loader import load_env
load_env()  # Loads env.ps1

# Then anywhere in the code:
import os
api_key = os.getenv('OPENAI_API_KEY')
```

The code never hardcodes the key - it always loads it from env.ps1.

---

## How It Stays Private

| File | Location | In Git? | Contains Secrets? |
|------|----------|---------|-------------------|
| **env.ps1** | `scripts/windows/` | ❌ NO (.gitignore) | ✓ YES (your real keys) |
| **env.ps1.template** | `scripts/windows/` | ✓ YES | ❌ NO (placeholders only) |
| Source code | `scripts/*.py` | ✓ YES | ❌ NO (uses os.getenv) |

**Result:** Your secrets are only on YOUR machine, never in git!

---

## Workflow Summary

```
┌─────────────────────┐
│ 1. Revoke old key   │ https://platform.openai.com/api-keys
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 2. Generate new key │
└──────────┬──────────┘
           │
           ▼
┌──────────────────────────────────────┐
│ 3. Edit C:\...\env.ps1               │
│    $env:OPENAI_API_KEY = "sk-proj-" │
└──────────┬───────────────────────────┘
           │
           ▼
┌──────────────────────┐
│ 4. Run pipeline      │ .\scripts\windows\run_pipeline.ps1
│    (auto-loads env)  │ (automatically loads env.ps1)
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ 5. Code uses key     │ os.getenv('OPENAI_API_KEY')
│    from env.ps1      │
└──────────────────────┘
```

---

## Troubleshooting

**Q: "OPENAI_API_KEY not set; skipping description enhancement"**
- A: You need to run `& .\scripts\windows\env.ps1` first to load the variable

**Q: How do I know if it's loaded?**
```powershell
& .\scripts\windows\env.ps1
echo $env:OPENAI_API_KEY  # Should print your key (or first 10 chars)
```

**Q: Can I hardcode the key in Python?**
- A: NO! That would commit it to git and expose it.
- Always use: `os.getenv('OPENAI_API_KEY')`

**Q: What if I change machines?**
- Copy the `env.ps1` file to your new machine
- The code will work the same way without changes

---

## Your Updated Files

✅ **env.ps1** - Added OPENAI_API_KEY section (replace placeholder)
✅ **env.ps1.template** - Updated template with OpenAI variables
✅ **Code** - Already uses `os.getenv()` (no changes needed)

That's it! Your setup is production-ready.
