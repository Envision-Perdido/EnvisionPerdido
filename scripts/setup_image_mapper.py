#!/usr/bin/env python3
"""
Image Mapper Setup & Management

This script helps you manage custom event images for the WordPress calendar.

Usage:
    python scripts/setup_image_mapper.py init
    python scripts/setup_image_mapper.py stats
    python scripts/setup_image_mapper.py verify

"""

import os
import sys
from pathlib import Path
import pandas as pd

# Configuration
BASE_DIR = Path(__file__).resolve().parent.parent
IMAGES_DIR = BASE_DIR / "data" / "event_images"
MAPPING_FILE = BASE_DIR / "data" / "event_image_mapping.csv"

def init_directories():
    """Create directories for image storage"""
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    print(f"✓ Created images directory: {IMAGES_DIR}")
    
    # Create a README
    readme = IMAGES_DIR / "README.txt"
    if not readme.exists():
        with open(readme, 'w') as f:
            f.write("""Event Images Directory
======================

Place supervisor-approved event images here. Supported formats:
- JPG / JPEG
- PNG
- GIF
- WebP

Naming convention:
Event images should match event titles exactly or be mapped in:
  data/event_image_mapping.csv

The pipeline will automatically:
1. Check for image mappings in event_image_mapping.csv
2. Upload images to WordPress
3. Attach as featured images to events

For help, see: docs/IMAGE_UPLOAD_GUIDE.md
""")
        print(f"✓ Created README in images directory")

def create_mapping_template(latest_csv=None):
    """Create mapping template from most recent events CSV"""
    if latest_csv is None:
        # Find most recent calendar_upload CSV
        pipeline_dir = BASE_DIR / "output" / "pipeline"
        csv_files = list(pipeline_dir.glob("calendar_upload_*.csv"))
        if not csv_files:
            print("✗ No events CSV found. Run the pipeline first.")
            return
        latest_csv = max(csv_files, key=lambda p: p.stat().st_mtime)
    
    print(f"Loading events from: {latest_csv}")
    events_df = pd.read_csv(latest_csv)
    
    # Create mapping template
    unique_titles = events_df['title'].unique()
    mapping_df = pd.DataFrame({
        'event_title': unique_titles,
        'image_filename': [''] * len(unique_titles),
        'notes': [''] * len(unique_titles)
    })
    
    mapping_df.to_csv(MAPPING_FILE, index=False)
    print(f"✓ Created mapping template: {MAPPING_FILE}")
    print(f"  Found {len(unique_titles)} unique events")
    print()
    print("Next steps:")
    print(f"  1. Place images in: {IMAGES_DIR}/")
    print(f"  2. Edit {MAPPING_FILE}")
    print(f"     - Fill 'image_filename' column with filenames")
    print(f"     - Example: 'brandon_styles.jpg'")
    print(f"  3. Run pipeline again - images will be automatically applied")
    print()
    return mapping_df

def show_stats():
    """Show image setup statistics"""
    print("=" * 60)
    print("IMAGE MAPPER STATISTICS")
    print("=" * 60)
    print()
    
    # Check images directory
    if IMAGES_DIR.exists():
        images = list(IMAGES_DIR.glob("*"))
        images = [f for f in images if f.is_file() and not f.name.startswith('.')]
        print(f"Images directory:     {IMAGES_DIR}")
        print(f"  Image files:        {len(images)}")
        if images:
            for img in images[:5]:
                size_kb = img.stat().st_size / 1024
                print(f"    - {img.name} ({size_kb:.1f} KB)")
            if len(images) > 5:
                print(f"    ... and {len(images) - 5} more")
    else:
        print(f"Images directory:     NOT CREATED")
        print(f"  Run: python scripts/setup_image_mapper.py init")
    print()
    
    # Check mapping file
    if MAPPING_FILE.exists():
        mapping_df = pd.read_csv(MAPPING_FILE)
        with_images = mapping_df['image_filename'].notna().sum()
        without_images = len(mapping_df) - with_images
        
        print(f"Mapping file:         {MAPPING_FILE}")
        print(f"  Total events:       {len(mapping_df)}")
        print(f"  With images:        {with_images}")
        print(f"  Without images:     {without_images}")
        
        if with_images > 0:
            print()
            print("Events with images mapped:")
            mapped = mapping_df[mapping_df['image_filename'].notna()]
            for _, row in mapped.iterrows():
                img_file = row['image_filename']
                img_path = IMAGES_DIR / img_file
                exists = "✓" if img_path.exists() else "✗"
                print(f"  {exists} {row['event_title'][:40]}")
                print(f"    → {img_file}")
    else:
        print(f"Mapping file:         NOT CREATED")
        print(f"  Run: python scripts/setup_image_mapper.py create-template")
    print()

def verify_mappings():
    """Verify all mapped images exist"""
    if not MAPPING_FILE.exists():
        print("✗ No mapping file found")
        return
    
    mapping_df = pd.read_csv(MAPPING_FILE)
    print("=" * 60)
    print("VERIFYING IMAGE MAPPINGS")
    print("=" * 60)
    print()
    
    missing = []
    found = []
    
    for _, row in mapping_df.iterrows():
        if pd.isna(row['image_filename']) or not str(row['image_filename']).strip():
            continue
        
        img_file = str(row['image_filename']).strip()
        img_path = IMAGES_DIR / img_file
        
        if img_path.exists():
            found.append((row['event_title'], img_file))
        else:
            missing.append((row['event_title'], img_file))
    
    if found:
        print(f"✓ Found {len(found)} images:")
        for title, filename in found[:5]:
            print(f"  ✓ {title[:40]}")
            print(f"    {filename}")
        if len(found) > 5:
            print(f"  ... and {len(found) - 5} more")
        print()
    
    if missing:
        print(f"✗ Missing {len(missing)} images:")
        for title, filename in missing:
            print(f"  ✗ {title[:40]}")
            print(f"    {filename} (not found in {IMAGES_DIR})")
        print()
        print("ACTION: Copy missing images to data/event_images/")
    else:
        print("✓ All mapped images found!")
    print()

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        show_stats()
        return
    
    command = sys.argv[1]
    
    if command == "init":
        init_directories()
        
    elif command == "create-template":
        init_directories()
        latest_csv = sys.argv[2] if len(sys.argv) > 2 else None
        create_mapping_template(latest_csv)
        
    elif command == "stats":
        show_stats()
        
    elif command == "verify":
        verify_mappings()
        
    else:
        print(f"Unknown command: {command}")
        print(__doc__)

if __name__ == "__main__":
    main()
