#!/usr/bin/env python3
"""
Validation Script: Google Sheets Integration Verification

This script validates that the Google Sheets integration is properly
installed and configured.
"""

import sys
import os
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def check_files_exist():
    """Check that all required files exist."""
    print("\n✓ Checking required files...")
    
    required_files = [
        'scripts/google_sheets_source.py',
        'tests/test_google_sheets_source.py',
        'docs/GOOGLE_SHEETS_SETUP.md',
        'docs/GOOGLE_SHEETS_IMPLEMENTATION_SUMMARY.md',
        'examples/google_sheets_format_example.py',
        'examples/google_sheets_integration_example.py',
    ]
    
    # Base dir is the parent of scripts directory
    base_dir = Path(__file__).parent.parent
    all_exist = True
    
    for file_path in required_files:
        full_path = base_dir / file_path
        exists = full_path.exists()
        status = "✓" if exists else "✗"
        print(f"  {status} {file_path}")
        all_exist = all_exist and exists
    
    return all_exist


def check_imports():
    """Check that modules can be imported."""
    print("\n✓ Checking module imports...")
    
    try:
        from scripts import google_sheets_source
        print("  ✓ google_sheets_source imported")
    except ImportError as e:
        print(f"  ✗ Failed to import google_sheets_source: {e}")
        return False
    
    try:
        from scripts import automated_pipeline
        print("  ✓ automated_pipeline imported")
    except ImportError as e:
        print(f"  ✗ Failed to import automated_pipeline: {e}")
        return False
    
    return True


def check_function_signatures():
    """Check that key functions exist with correct signatures."""
    print("\n✓ Checking function signatures...")
    
    from scripts import google_sheets_source
    import inspect
    
    functions_to_check = [
        ('get_sheets_config', []),
        ('load_service_account_credentials', ['credentials_path', 'credentials_b64']),
        ('fetch_sheet_rows', ['spreadsheet_id', 'sheet_range', 'credentials']),
        ('normalize_header', ['header']),
        ('rows_to_dicts', ['rows']),
        ('parse_datetime_flexible', ['date_str', 'time_str']),
        ('map_sheet_row_to_event', ['row_dict', 'row_number', 'column_mapping']),
        ('get_events_from_sheets', ['column_mapping', 'dry_run']),
    ]
    
    all_ok = True
    for func_name, expected_params in functions_to_check:
        if not hasattr(google_sheets_source, func_name):
            print(f"  ✗ Function not found: {func_name}")
            all_ok = False
            continue
        
        func = getattr(google_sheets_source, func_name)
        sig = inspect.signature(func)
        params = list(sig.parameters.keys())
        
        # Check if all expected params are in function signature
        all_present = all(p in params for p in expected_params)
        status = "✓" if all_present else "✗"
        print(f"  {status} {func_name}({', '.join(params[:3])}...)")
        all_ok = all_ok and all_present
    
    return all_ok


def check_tests():
    """Check that tests can be loaded."""
    print("\n✓ Checking test suite...")
    
    try:
        import tests.test_google_sheets_source as test_module
        
        # Count test classes
        test_classes = [name for name in dir(test_module) if name.startswith('Test')]
        print(f"  ✓ Found {len(test_classes)} test classes")
        
        # Count test methods
        test_count = 0
        for class_name in test_classes:
            test_class = getattr(test_module, class_name)
            methods = [m for m in dir(test_class) if m.startswith('test_')]
            test_count += len(methods)
        
        print(f"  ✓ Found {test_count} test methods")
        return test_count >= 40  # Should have ~41 tests
    
    except Exception as e:
        print(f"  ✗ Failed to load tests: {e}")
        return False


def check_pipeline_integration():
    """Check that Sheets source is integrated in pipeline."""
    print("\n✓ Checking pipeline integration...")
    
    try:
        from scripts import automated_pipeline
        import inspect
        
        # Get source code of scrape_events function
        source = inspect.getsource(automated_pipeline.scrape_events)
        
        # Check for google_sheets reference
        if 'google_sheets' in source:
            print("  ✓ google_sheets source referenced in scrape_events()")
            if 'google_sheets_source' in source:
                print("  ✓ google_sheets_source module imported in scrape_events()")
            return True
        else:
            print("  ✗ google_sheets not found in scrape_events()")
            return False
    
    except Exception as e:
        print(f"  ✗ Failed to check pipeline integration: {e}")
        return False


def check_documentation():
    """Check that documentation files are present."""
    print("\n✓ Checking documentation...")
    
    # Base dir is parent of scripts directory
    base_dir = Path(__file__).parent.parent
    
    docs_to_check = [
        ('GOOGLE_SHEETS_SETUP.md', 'setup guide'),
        ('GOOGLE_SHEETS_IMPLEMENTATION_SUMMARY.md', 'implementation summary'),
    ]
    
    all_ok = True
    for doc_file, desc in docs_to_check:
        path = base_dir / 'docs' / doc_file
        if path.exists():
            size_kb = path.stat().st_size / 1024
            print(f"  ✓ {doc_file} ({size_kb:.1f} KB)")
        else:
            print(f"  ✗ {doc_file} not found")
            all_ok = False
    
    return all_ok


def check_environment_vars():
    """Check if environment variables are set (informational)."""
    print("\n✓ Checking environment variables...")
    
    vars_to_check = [
        'SHEETS_SPREADSHEET_ID',
        'GOOGLE_APPLICATION_CREDENTIALS',
        'GOOGLE_SHEETS_SA_JSON_B64',
    ]
    
    configured = False
    for var in vars_to_check:
        is_set = var in os.environ
        status = "✓" if is_set else "○"
        print(f"  {status} {var}: {'SET' if is_set else 'not set'}")
        configured = configured or is_set
    
    if not configured:
        print("\n  ℹ️  To use Google Sheets:")
        print("     1. Set SHEETS_SPREADSHEET_ID")
        print("     2. Set GOOGLE_APPLICATION_CREDENTIALS or GOOGLE_SHEETS_SA_JSON_B64")
        print("     See docs/GOOGLE_SHEETS_SETUP.md for instructions")
    
    return True


def main():
    """Run all validation checks."""
    print("\n" + "=" * 70)
    print("Google Sheets Integration Verification")
    print("=" * 70)
    
    checks = [
        ("Files", check_files_exist),
        ("Imports", check_imports),
        ("Functions", check_function_signatures),
        ("Tests", check_tests),
        ("Pipeline Integration", check_pipeline_integration),
        ("Documentation", check_documentation),
        ("Environment Variables", check_environment_vars),
    ]
    
    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"\n✗ Check '{name}' failed with exception: {e}")
            results[name] = False
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    all_passed = True
    for name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
        all_passed = all_passed and passed
    
    print("=" * 70)
    
    if all_passed:
        print("\n✅ All validation checks passed!")
        print("\nGoogle Sheets integration is ready to use.")
        print("See docs/GOOGLE_SHEETS_SETUP.md for configuration instructions.")
        return 0
    else:
        print("\n❌ Some validation checks failed.")
        print("Please review the errors above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
