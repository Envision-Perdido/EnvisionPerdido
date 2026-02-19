#!/usr/bin/env python3
"""
Comprehensive Module Import Verification
Tests all functional subdirectories for correct import structure
"""

import sys
import os
sys.path.insert(0, 'scripts')

tests_passed = []
tests_failed = []

print("\n" + "="*70)
print("COMPREHENSIVE MODULE IMPORT TEST".center(70))
print("="*70)

# Test Core Utilities
print("\n📦 Testing Core Utilities...")
try:
    from core.env_loader import load_env
    tests_passed.append("✓ core.env_loader (environment configuration)")
except Exception as e:
    tests_failed.append(f"✗ core.env_loader: {e}")

try:
    from core.logger import get_logger
    tests_passed.append("✓ core.logger (structured logging)")
except Exception as e:
    tests_failed.append(f"✗ core.logger: {e}")

try:
    from core.tag_taxonomy import TagTaxonomy
    tests_passed.append("✓ core.tag_taxonomy (tag vocabulary)")
except Exception as e:
    tests_failed.append(f"✗ core.tag_taxonomy: {e}")

try:
    from core.health_check import run_health_check
    tests_passed.append("✓ core.health_check (system validation)")
except Exception as e:
    tests_failed.append(f"✗ core.health_check: {e}")

try:
    from core.venue_registry import VenueRegistry
    tests_passed.append("✓ core.venue_registry (known venues)")
except Exception as e:
    tests_failed.append(f"✗ core.venue_registry: {e}")

# Test ML Modules
print("📦 Testing ML Modules...")
try:
    from ml.svm_train_from_file import prepare_training_data
    tests_passed.append("✓ ml.svm_train_from_file (model training)")
except Exception as e:
    tests_failed.append(f"✗ ml.svm_train_from_file: {e}")

try:
    from ml.svm_tag_events import load_classifier
    tests_passed.append("✓ ml.svm_tag_events (event classification)")
except Exception as e:
    tests_failed.append(f"✗ ml.svm_tag_events: {e}")

try:
    from ml.auto_label_and_train import AutoLabelAndTrain
    tests_passed.append("✓ ml.auto_label_and_train (automated training)")
except Exception as e:
    tests_failed.append(f"✗ ml.auto_label_and_train: {e}")

try:
    from ml.smart_label_helper import SmartLabelHelper
    tests_passed.append("✓ ml.smart_label_helper (interactive labeling)")
except Exception as e:
    tests_failed.append(f"✗ ml.smart_label_helper: {e}")

# Test Data Processing
print("📦 Testing Data Processing Modules...")
try:
    from data_processing.event_normalizer import EventNormalizer
    tests_passed.append("✓ data_processing.event_normalizer (data enrichment)")
except Exception as e:
    tests_failed.append(f"✗ data_processing.event_normalizer: {e}")

try:
    from data_processing.fill_recurring_labels import FillRecurringLabels
    tests_passed.append("✓ data_processing.fill_recurring_labels (label propagation)")
except Exception as e:
    tests_failed.append(f"✗ data_processing.fill_recurring_labels: {e}")

try:
    from data_processing.fix_event_times import FixEventTimes
    tests_passed.append("✓ data_processing.fix_event_times (time standardization)")
except Exception as e:
    tests_failed.append(f"✗ data_processing.fix_event_times: {e}")

# Test Scrapers
print("📦 Testing Scraper Modules...")
try:
    from scrapers.wren_haven_scraper import WrenHavenScraper
    tests_passed.append("✓ scrapers.wren_haven_scraper (web scraper)")
except Exception as e:
    tests_failed.append(f"✗ scrapers.wren_haven_scraper: {e}")

try:
    from scrapers.google_sheets_source import GoogleSheetEventSource
    tests_passed.append("✓ scrapers.google_sheets_source (Sheets integration)")
except Exception as e:
    tests_failed.append(f"✗ scrapers.google_sheets_source: {e}")

try:
    from scrapers import Envision_Perdido_DataCollection
    tests_passed.append("✓ scrapers.Envision_Perdido_DataCollection (chamber scraper)")
except Exception as e:
    tests_failed.append(f"✗ scrapers.Envision_Perdido_DataCollection: {e}")

# Test Entry Points
print("📦 Testing Entry Point Modules...")
try:
    from pipelines import automated_pipeline
    tests_passed.append("✓ pipelines.automated_pipeline (main workflow)")
except Exception as e:
    tests_failed.append(f"✗ pipelines.automated_pipeline: {e}")

try:
    from pipelines import wordpress_uploader
    tests_passed.append("✓ pipelines.wordpress_uploader (WP REST integration)")
except Exception as e:
    tests_failed.append(f"✗ pipelines.wordpress_uploader: {e}")

# Print results
print("\n" + "="*70)
print(f"\n✅ PASSED: {len(tests_passed)}")
for test in tests_passed:
    print(f"  {test}")

if tests_failed:
    print(f"\n❌ FAILED: {len(tests_failed)}")
    for test in tests_failed:
        print(f"  {test}")
    print(f"\nNote: Some optional dependencies may not be installed.")
    print(f"      This is not a failure if the underlying module is present.")
else:
    print("\n🎉 ALL IMPORTS SUCCESSFUL - PROJECT STRUCTURE VALIDATED!")

print(f"\nSummary: {len(tests_passed)}/{len(tests_passed)+len(tests_failed)} modules verified")
print("="*70 + "\n")
