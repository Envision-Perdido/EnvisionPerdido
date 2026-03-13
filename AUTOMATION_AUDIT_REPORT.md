# EnvisionPerdido Automation & Tooling Audit Report
**Date:** March 12, 2026 | **Team Size:** 2 people | **Total Automation Files:** 40+

---

## EXECUTIVE SUMMARY

This codebase has **significant automation complexity** for a 2-person team. While the core pipeline automation is excellent and necessary, there is **~30% redundancy** across configuration files, scripting entry points, and AI agent guidance.

**Bottom Line:** The project is over-engineered for optimal team velocity. Consolidation recommended in 3 areas:
1. Multiple entry point scripts (should standardize on Makefile)
2. Overlapping ML training scripts (should pick one workflow)
3. Duplicate agent/copilot configurations (should consolidate guidance)

---

## DETAILED INVENTORY

### 1. GITHUB ACTIONS WORKFLOWS (5 files, ~150 lines)

| File | Purpose | Complexity | Necessary? | Issues |
|------|---------|-----------|-----------|--------|
| **lint.yml** | Code quality (Ruff linting) | LOW | ✅ YES | Only runs on `main` (should run on `dev` too) |
| **test.yml** | Unit tests (pytest) | LOW | ✅ YES | Good; only ~29 lines |
| **smoketest.yml** | Epoch validation (evcal_srow) | MEDIUM | ✅ YES | Excellent; catches timezone regressions without hitting network |
| **health-check.yml** | Weekly WordPress API monitoring | HIGH | ⚠️ QUESTIONABLE | Requires 7 GitHub Secrets; only 1 scheduled job; could alert manually instead |
| **stale.yml** | Auto-close inactive issues | LOW | ❌ NO | Unnecessary for 2-person team; creates extra friction |

**Assessment:** Keep core workflows (lint, test, smoketest). Consider removing stale.yml; make health-check optional.

---

### 2. GITHUB BOT & TEMPLATES

| File | Purpose | Necessary? | Recommendation |
|------|---------|-----------|-------------|
| **dependabot.yml** | Auto-update dependencies | ❌ NO (15 lines) | Disable; creates noise for small team |
| **pull_request_template.md** | PR checklist enforcement | ✅ YES (70 lines) | Excellent; prevents accidental uploads |
| **ISSUE_TEMPLATE/** (3 files) | Issue structure | ✅ YES | Good; helps structure reporting |

**Assessment:** PR template is valuable safety feature. Remove Dependabot.

---

### 3. COPILOT / AGENT CONFIGURATIONS

| File | Purpose | Lines | Necessary? | Issue |
|------|---------|-------|-----------|-------|
| **copilot-instructions.md** | AI agent orientation | 250+ | ⚠️ PARTIAL | Dense; duplicates docs/QUICKSTART.md |
| **.github/agents/my-agent.agent.md** | Custom agent guidance | 20 | ⚠️ PARTIAL | Overlaps with copilot-instructions.md |
| **AGENTS.md** | Codex guidance | 60 | ❌ NO | Redundant with both above |

**Critical Issue:** Three separate agent configs with overlapping content. 

**Recommendation:** 
- Keep only `.github/agents/my-agent.agent.md` (minimal, clear)
- Move `copilot-instructions.md` content to `docs/DEVELOPER_GUIDE.md`
- Delete `AGENTS.md`

---

### 4. LINTING & CODE QUALITY

| File | Purpose | Necessary? |
|------|---------|-----------|
| **.ruff.toml** | Ruff linter config (40 lines) | ✅ YES |

Assessment: Well-tuned; keeps this.

---

### 5. SHELL SCRIPTS (BASH, 8 files)

| Script | Lines | Purpose | Complexity | Necessary? | Issues |
|--------|-------|---------|-----------|-----------|--------|
| **run_pipeline_with_smoketest.sh** | 28 | Run pipeline + epoch check | LOW | ⚠️ MARGINAL | Duplicates Makefile target; adds wrapper layering |
| **run_with_venv.sh** | 27 | Execute Python in home venv | LOW | ❌ NO | Local `.venv` is simpler; hard-coded path ($HOME/.virtualenvs) |
| **deploy-and-run.sh** | 120+ | Remote deployment wrapper | HIGH | ⚠️ MARGINAL | Over-engineered for 2-person team; good for CI/CD but overkill for local |
| **new-branch.sh** | 80+ | Interactive branch creator | LOW | ✅ YES | Enforces naming conventions; good workflow tool |
| **load_env.sh** | 11 | Load .env | TRIVIAL | ✅ YES | Essential |
| **verify-setup.sh** | TBD | Verify environment | TBD | ✅ YES | TBD |
| **verify_security.sh** | TBD | Security checks | TBD | ⚠️ MARGINAL | Possibly redundant with deploy-and-run.sh checks |
| **run_delete_all_events.sh** | TBD | Delete all WordPress events | TBD | ❌ NO | **DANGEROUS** - should not exist or require per-event confirmation |

**Assessment:** Significant overlap. **Standardize on Makefile** as primary entry point:
- Remove `run_pipeline_with_smoketest.sh` (add as Makefile target)
- Remove `run_with_venv.sh` (use local venv)
- Keep `new-branch.sh` (good tool)
- Keep `deploy-and-run.sh` for CI/CD only

---

### 6. POWERSHELL SCRIPTS (WINDOWS, 6 files)

| Script | Lines | Purpose | Necessary? | Issues |
|--------|-------|---------|-----------|--------|
| **setup_scheduled_tasks.ps1** | 120+ | Create Windows scheduled tasks | ⚠️ MARGINAL | Requires admin; fragile; tasks often fail silently |
| **run_pipeline.ps1** | 29 | Run pipeline on Windows | ✅ YES (if team uses Windows) | Good Windows parity |
| **run_health_check.ps1** | 26 | Health check wrapper | ✅ YES (if team uses Windows) | Good Windows parity |
| **run_fix_event_times.ps1** | 26 | Fix event times | ⚠️ OPTIONAL | Specialized; infrequent use |
| **run_delete_all_events.ps1** | 26 | Delete all events | ❌ NO | **DANGEROUS** - should require confirmation per-event |
| **new-branch.ps1** | 90+ | Branch creator (Windows) | ✅ YES (if team uses Windows) | Good parity with bash version |

**Assessment:** 
- Keep core run scripts for Windows developers (parity with bash)
- **Remove or fix** `setup_scheduled_tasks.ps1` (operational burden; fragile)
- **Delete** `run_delete_all_events.ps1` or add interactive confirmation

---

### 7. MAKEFILE (Primary Entry Point)

**180+ lines | 11 targets**

| Target | Purpose | Safety | Used Frequently? |
|--------|---------|--------|-----------------|
| `make setup` | Create venv + install deps | ✅ YES | Infrequent (1x per env) |
| `make install` | Install deps | ✅ YES | Infrequent |
| `make test` | Run pytest | ✅ YES | Regularly |
| `make lint` | Run ruff | ✅ YES | Regularly |
| `make verify` | Check setup (env, artifacts, venv) | ✅ YES | Infrequent |
| `make dry-run` | **AUTO_UPLOAD=false (SAFE)** | ✅ EXCELLENT | Regularly |
| `make run-pipeline` | Full pipeline (AUTO_UPLOAD controlled) | ✅ YES | Weekly+ |
| `make run-uploader` | Interactive WordPress uploader | ✅ YES | Weekly+ |
| `make regenerate-descriptions-dry-run` | Preview OpenAI enhancement | ✅ YES | Infrequent |
| `make regenerate-descriptions` | Batch OpenAI enhancement | ✅ YES | Monthly |
| `make regenerate-descriptions-sync` | Sync OpenAI enhancement | ✅ YES | Infrequent |

**Assessment:** Excellent design; cross-platform; good safety patterns. **Keep as primary entry point.**

---

### 8. CORE PYTHON AUTOMATION SCRIPTS

#### **TIER 1: Required Pipeline (Essential)**

| Script | Lines | Purpose | Necessary? |
|--------|-------|---------|-----------|
| **automated_pipeline.py** | 650+ | Main: scrape→classify→export→email→upload | ✅ YES - Core |
| **wordpress_uploader.py** | TBD | Interactive uploader (dry-run first, drafts safe) | ✅ YES - Core |
| **Envision_Perdido_DataCollection.py** | TBD | Scraper + ICS parser | ✅ YES - Core |
| **event_normalizer.py** | TBD | Data normalization | ✅ YES - Core |
| **env_loader.py** | 50+ | Environment variable loading | ✅ YES - Core |
| **logger.py** | 50+ | Logging + metrics | ✅ YES - Core |

**Assessment:** Essential, well-maintained pipeline. Keep all.

---

#### **TIER 2: ML Training & Labeling (Regular Use)**

| Script | Lines | Purpose | Necessary? | Issue |
|--------|-------|---------|-----------|-------|
| **auto_label_and_train.py** | 100+ | Auto-label + retrain SVM | ✅ YES | Primary training workflow |
| **pseudo_label_and_retrain.py** | 80+ | High-confidence pseudo-labeling | ⚠️ OPTIONAL | Advanced strategy; monthly use |
| **svm_train_from_file.py** | 150+ | Train SVM from CSV/JSON | ✅ YES | Flexible training entry point |
| **merge_and_propagate_labels.py** | 50+ | Merge manual + predicted, propagate series | ✅ YES | Pipeline step |
| **fill_recurring_labels.py** | TBD | Fill recurring event labels | ⚠️ MARGINAL | Possibly redundant with merge_and_propagate |
| **smart_label_helper.py** | 80+ | Predict + flag low-confidence | ⚠️ OPTIONAL | Interactive workflow; nice-to-have |
| **consolidate_training_data.py** | TBD | Merge datasets | ⚠️ OPTIONAL | Data prep utility |
| **events_to_labelset.py** | TBD | Convert to labelset format | ⚠️ OPTIONAL | Data transformation |

**Critical Issue:** **5+ overlapping labeling scripts.** Unclear which workflow to use.

**Recommendation:** Consolidate into single `label_and_retrain.py` with strategic options (auto-label, pseudo-label, propagate as sub-steps).

---

#### **TIER 3: Maintenance & Utilities**

| Script | Lines | Purpose | Necessary? |
|--------|-------|---------|-----------|
| **health_check.py** | 80+ | Monitor WordPress API + calendar | ✅ YES |
| **regenerate_descriptions.py** | 200+ | OpenAI description enhancement (Batch/Sync) | ⚠️ OPTIONAL - Nice-to-have |
| **audit_datasets.py** | 50+ | Audit data files | ⚠️ OPTIONAL - Diagnostics |
| **venue_registry.py**, **tag_taxonomy.py**, **svm_tag_events.py** | TBD | Venue/tag management | ⚠️ OPTIONAL - Niche tools |
| **wren_haven_scraper.py** | TBD | Wren Haven event scraper | ✅ YES (if source active) |
| **browser_bootstrap.py** | TBD | Browser artifacts cache | ⚠️ OPTIONAL |
| **modelViewer.py** | TBD | Model visualization | ❌ NO - Dev only |
| **setup_image_mapper.py** | TBD | Image mapping | ⚠️ OPTIONAL - Setup utility |

**Assessment:** Good utilities; some development-only scripts should be moved to tests/.

---

### 9. DEVELOPMENT/DEBUG SCRIPTS (`scripts/dev/`, 8 files)

| Script | Purpose | Necessary? | Should Be In |
|--------|---------|-----------|------------|
| **check_evcal_srow.py** | Validate EventON epochs | ✅ YES | Keep here (used in CI) |
| **debug_event_meta.py** | Metadata debugging | ❌ NO | tests/dev/ |
| **test_wp_auth.py** | Auth testing | ❌ NO | tests/dev/ |
| **test_local_epoch.py** | Epoch validation | ❌ NO | tests/dev/ |
| **test_hour_format.py** | Format testing | ❌ NO | tests/dev/ |
| **test_epoch_approaches.py** | Strategy comparison | ❌ NO | tests/dev/ or archive/ |
| **test_delete_operation.py** | Delete safety | ❌ NO | tests/dev/ |
| **profile_inference.py** | Performance profiling | ❌ NO | tests/dev/ or archive/ |
| **visualize_pipeline.py** | Pipeline visualization | ❌ NO | tests/dev/ or archive/ |

**Assessment:** Most should be in `tests/dev/` not `scripts/dev/`. Only `check_evcal_srow.py` should stay in scripts/.

---

### 10. SKILLS FRAMEWORK (6 domain skills)

**Location:** `skills/calendar-*/`

| Skill | Purpose | Used By Team? | Used By AI? |
|--------|---------|--------------|-----------|
| calendar-env-setup | Configure env variables | ⚠️ PARTIAL | ✅ YES |
| calendar-docker-build | Build container | ⚠️ MARGINAL | ✅ YES |
| calendar-run-pipeline | Execute pipeline | ⚠️ MARGINAL | ✅ YES |
| calendar-wordpress-upload | Upload events | ⚠️ MARGINAL | ✅ YES |
| calendar-health-check | Health monitoring | ⚠️ MARGINAL | ✅ YES |
| calendar-shell | Interactive shell | ⚠️ MARGINAL | ✅ YES |

**Assessment:** Well-organized for AI agents; adds indirection for humans (team should use Makefile directly).

---

## REDUNDANCY ANALYSIS

### 🔴 CRITICAL: Multiple Entry Points to Same Function

You can run the pipeline in **6+ different ways:**

```bash
make run-pipeline                           # Makefile
python scripts/automated_pipeline.py        # Direct
./scripts/run_pipeline_with_smoketest.sh    # Bash wrapper
./scripts/windows/run_pipeline.ps1          # PowerShell
docker-compose exec app make run-pipeline   # Docker (implied)
skills/calendar-run-pipeline/SKILL.md       # AI agent skill
```

**For 2-person team:** This causes analysis paralysis. **Standardize on Makefile.**

---

### 🟡 MODERATE: Overlapping Labeling Workflows

5 scripts handle labeling/training:
- `auto_label_and_train.py` (main)
- `pseudo_label_and_retrain.py` (advanced)
- `merge_and_propagate_labels.py` (step)
- `fill_recurring_labels.py` (series)
- `smart_label_helper.py` (interactive)

**For 2-person team:** Consolidate into single workflow with strategic options.

---

### 🟡 MODERATE: Duplicate Agent Configuration

Three files guide AI agents:
- `copilot-instructions.md` (250 lines)
- `.github/agents/my-agent.agent.md` (20 lines)
- `AGENTS.md` (60 lines)

**Overlap:** All describe the same project; unclear precedence.

**Fix:** Keep only `.github/agents/my-agent.agent.md`; reference docs from there.

---

### 🟡 MODERATE: Multiple Environment Setup Methods

- `.env` (implicit for Unix)
- `.env.ps1` (Windows)
- `.env.ps1.example`
- `.env.ps1.template`
- `env.ps1` (Windows)
- Examples hardcoded in `copilot-instructions.md`

**For 2-person team:** One source of truth (README or docs/ENV_SETUP.md).

---

## SAFETY FEATURES (EXCELLENT)

✅ **Confidence thresholds:** Events < 0.75 confidence flagged for review
✅ **AUTO_UPLOAD env var:** Pipeline defaults to false (safe-by-default)
✅ **Dry-run patterns:** WordPress uploader runs dry-run first, creates drafts
✅ **PR template:** Enforces security checklist + branch conventions
✅ **Smoketest:** Validates timezone logic without scraping network

**Assessment:** Very strong safety culture. Maintain these patterns.

---

## RECOMMENDATIONS FOR 2-PERSON TEAM

### 🔴 IMMEDIATE (1 week)

1. **Standardize entry points** (reduce confusion)
   - Use `make run-pipeline` as canonical entry point
   - Remove `run_pipeline_with_smoketest.sh` (make a Makefile target instead)
   - Keep `new-branch.sh` (good tool)
   - Document other scripts as "deprecated" or "CI/CD only"

2. **Disable unnecessary automation**
   - Disable Dependabot (set schedule: never)
   - Optional: disable stale PR closer (it creates friction for small teams)

3. **Consolidate agent configs**
   - Delete `AGENTS.md`
   - Delete or move `copilot-instructions.md` to `docs/DEVELOPER_GUIDE.md`
   - Keep only `.github/agents/my-agent.agent.md` (minimal, clear)

### 🟡 SHORT-TERM (First month)

1. **Add safety checks**
   - Make `run_delete_all_events.ps1` require interactive confirmation per event (or delete entirely)
   - Add dry-run to any scripts that modify WordPress

2. **Move dev scripts to tests/**
   - Move `scripts/dev/*` to `tests/dev/`
   - Keep `check_evcal_srow.py` in `scripts/dev/` (used in CI)

3. **Consolidate labeling workflows**
   - Pick primary workflow: recommend `auto_label_and_train.py`
   - Archive redundant scripts to `archive/` or `docs/deprecated/`
   - Document decision in `docs/ML_TRAINING_WORKFLOW.md`

4. **Create single environment setup guide**
   - Consolidate `.env*` examples into `docs/ENV_SETUP.md`
   - Remove hardcoded examples from `copilot-instructions.md`

### 🟢 LONG-TERM (Next quarter)

1. **Audit for unused scripts**
   - `modelViewer.py` – dev only, can delete
   - `venue_registry.py`, `tag_taxonomy.py` – check if in use
   - Experiment scripts in `scripts/ml/`, `scripts/macos/` – archive or delete

2. **Consider simplifying Windows automation**
   - `setup_scheduled_tasks.ps1` is operational burden; remove unless actively used
   - Keep core run scripts for Windows parity

3. **Document automation decisions**
   - Create `docs/ARCHITECTURE_AUTOMATION.md` explaining:
     - Why Makefile is canonical entry point
     - Which scripts to use for which tasks
     - How AI agents should be guided

---

## COMPLEXITY SCORECARD

| Component | Complexity | Necessary | Critical Issues |
|-----------|-----------|-----------|------------|
| Core Pipeline (T1) | HIGH | ✅ YES | None - well-designed |
| ML Training (T2) | MEDIUM | ✅ YES | 5 overlapping scripts |
| Utilities (T3) | MEDIUM | ⚠️ MIXED | Some are dev-only |
| Entry Points | HIGH | ⚠️ REDUNDANT | 6+ ways to run same thing |
| CI/CD | MEDIUM | ✅ YES | Stale bot is unnecessary |
| Agent Config | MEDIUM | ⚠️ PARTIAL | 3 overlapping files |
| Windows Scripts | MEDIUM | ⚠️ MIXED | Scheduled tasks are fragile |
| Safety Features | N/A | ✅ YES | Excellent, keep all |

---

## FILES REQUIRING IMMEDIATE ACTION

| Path | Action | Rationale |
|------|--------|-----------|
| [.github/dependabot.yml](.github/dependabot.yml) | Disable (set schedule: never) | Creates noise for small team |
| [AGENTS.md](AGENTS.md) | Delete | Redundant with `.github/agents/my-agent.agent.md` |
| [.github/copilot-instructions.md](.github/copilot-instructions.md) | Move to `docs/` | Duplicates QUICKSTART.md |
| [scripts/run_pipeline_with_smoketest.sh](scripts/run_pipeline_with_smoketest.sh) | Remove (make Makefile target) | Adds wrapper layer |
| [scripts/run_with_venv.sh](scripts/run_with_venv.sh) | Remove (use .venv) | Hard-coded paths; local venv is simpler |
| [scripts/windows/setup_scheduled_tasks.ps1](scripts/windows/setup_scheduled_tasks.ps1) | Review or remove | Operational burden; fragile; silent failures |
| [scripts/windows/run_delete_all_events.ps1](scripts/windows/run_delete_all_events.ps1) | Add confirmation or delete | **DANGEROUS** - no safety checks |
| [scripts/dev/](scripts/dev/) | Move to `tests/dev/` | Clean up scripts directory |

---

## SUMMARY

✅ **Strengths:**
- Excellent core pipeline automation
- Strong safety features (dry-run, confidence thresholds, PR enforcements)
- Good cross-platform support (bash/PowerShell)
- Well-designed Makefile

❌ **Weaknesses:**
- Too many entry points (causes confusion)
- Redundant labeling scripts (unclear workflow)
- Duplicate agent configurations
- Development scripts mixed into scripts/ directory
- Over-engineered for 2-person team

🎯 **Action Item:** Consolidate around Makefile as canonical entry point; eliminate redundancy; keep safety features.

---

**Questions or clarifications needed?** See [copilot-instructions.md](.github/copilot-instructions.md) or docs/QUICKSTART.md.
