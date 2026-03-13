# Development & Debug Scripts

This directory contains development-only scripts for debugging, profiling, and testing. These scripts are **not part of the main pipeline** and should only be used for local development and troubleshooting.

## Scripts

- `debug_event_meta.py` - Debug WordPress event metadata
- `profile_inference.py` - Profile SVM inference performance
- `test_delete_operation.py` - Test deletion operation behavior
- `test_epoch_approaches.py` - Compare different epoch validation approaches
- `test_hour_format.py` - Test time format conversions
- `test_local_epoch.py` - Test local epoch calculations
- `test_wp_auth.py` - Test WordPress authentication

## Notes

- These scripts are for local development only
- Do not use these in production or CI/CD pipelines
- See `scripts/dev/check_evcal_srow.py` for the production epoch validation test (used in CI)
