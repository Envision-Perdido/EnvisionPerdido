# Deprecated Scripts

This directory contains scripts that have been archived due to consolidation efforts for a 2-person team workflow. These scripts are kept for historical reference but should not be used for new development.

## Archived ML Training Scripts

### Why Archived?

The project had 5 overlapping ML training workflows that created confusion about which workflow to use:
- `auto_label_and_train.py` ← **PRIMARY WORKFLOW (kept in scripts/)**
- `pseudo_label_and_retrain.py`
- `merge_and_propagate_labels.py`
- `fill_recurring_labels.py`
- `smart_label_helper.py`

To simplify the workflow for a 2-person team, the primary workflow was kept and the others archived here. If you need functionality from these scripts, consider integrating them into the primary workflow or opening an issue to discuss re-enabling them.

### Files in This Directory

- `pseudo_label_and_retrain.py` - Advanced pseudo-labeling strategy
- `merge_and_propagate_labels.py` - Label merging and series propagation
- `fill_recurring_labels.py` - Recurring event label filling
- `smart_label_helper.py` - Interactive prediction with low-confidence flagging

## Restoring a Deprecated Script

If you need to restore one of these scripts:

```bash
git log --all --full-history -- scripts/<script-name>
git show <commit>:scripts/<script-name> > scripts/<script-name>
```

Or contact the team to discuss whether it should be restored permanently.

---

See `docs/AUTOMATION_AUDIT_REPORT.md` for the full consolidation analysis.
