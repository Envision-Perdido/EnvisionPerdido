#!/usr/bin/env python3
"""
Manual Image Management for Events

This script helps you map custom images (provided by your supervisor) to events.
It creates/updates a CSV mapping file that associates event titles with image files.
"""

import pandas as pd
import os
from pathlib import Path

# Configuration
IMAGES_DIR = "data/event_images"  # Where supervisor's images will be stored
MAPPING_FILE = "data/event_image_mapping.csv"  # CSV that maps events to images

def create_images_directory():
    """Create directory for storing event images"""
    Path(IMAGES_DIR).mkdir(parents=True, exist_ok=True)
    print(f"Created images directory: {IMAGES_DIR}")
    print(f"Place your supervisor's images in this folder.")

def create_mapping_template(events_csv_path):
    """
    Create a template mapping file from existing events CSV.
    Your supervisor can fill in the image filenames.
    """
    # Load existing events
    events_df = pd.read_csv(events_csv_path)
    
    # Create mapping template with event titles and empty image column
    mapping_df = pd.DataFrame({
        'event_title': events_df['title'].unique(),
        'image_filename': '',  # To be filled in manually
        'notes': ''  # Optional notes about the image
    })
    
    mapping_df.to_csv(MAPPING_FILE, index=False)
    print(f"\nCreated mapping template: {MAPPING_FILE}")
    print(f"Found {len(mapping_df)} unique events")
    print("\nNext steps:")
    print(f"1. Have your supervisor place images in: {IMAGES_DIR}/")
    print(f"2. Edit {MAPPING_FILE} to fill in image_filename column")
    print(f"3. Run apply_image_mapping() to merge images with events")
    
    return mapping_df

def apply_image_mapping(events_csv_path, output_csv_path=None):
    """
    Apply the image mapping to events CSV by adding image_url column
    with local file paths.
    """
    if not os.path.exists(MAPPING_FILE):
        print(f"Error: Mapping file not found: {MAPPING_FILE}")
        print("Run create_mapping_template() first")
        return None
    
    # Load events and mapping
    events_df = pd.read_csv(events_csv_path)
    mapping_df = pd.read_csv(MAPPING_FILE)
    
    # Create mapping dict: title -> image filename
    image_map = {}
    for _, row in mapping_df.iterrows():
        if pd.notna(row['image_filename']) and row['image_filename'].strip():
            title = row['event_title']
            filename = row['image_filename'].strip()
            # Convert to full path
            image_path = os.path.abspath(os.path.join(IMAGES_DIR, filename))
            image_map[title] = image_path
    
    # Apply mapping to events
    events_df['image_url'] = events_df['title'].map(image_map)
    
    # Validate images exist
    missing_images = []
    for idx, row in events_df.iterrows():
        if pd.notna(row['image_url']):
            if not os.path.exists(row['image_url']):
                missing_images.append(row['image_url'])
    
    if missing_images:
        print(f"\nWarning: {len(missing_images)} image files not found:")
        for img in missing_images[:5]:
            print(f"  - {img}")
        if len(missing_images) > 5:
            print(f"  ... and {len(missing_images) - 5} more")
    
    # Save updated CSV
    if output_csv_path is None:
        output_csv_path = events_csv_path.replace('.csv', '_with_images.csv')
    
    events_df.to_csv(output_csv_path, index=False)
    
    print(f"\nApplied image mapping:")
    print(f"  Total events: {len(events_df)}")
    print(f"  Events with images: {events_df['image_url'].notna().sum()}")
    print(f"  Events without images: {events_df['image_url'].isna().sum()}")
    print(f"\nSaved to: {output_csv_path}")
    
    return events_df

def list_unmapped_images():
    """List images in the images directory that aren't mapped to any event"""
    if not os.path.exists(IMAGES_DIR):
        print(f"Images directory doesn't exist: {IMAGES_DIR}")
        return
    
    if not os.path.exists(MAPPING_FILE):
        print(f"Mapping file doesn't exist: {MAPPING_FILE}")
        return
    
    # Get all image files
    image_files = set()
    for ext in ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.webp']:
        image_files.update([f.name for f in Path(IMAGES_DIR).glob(ext)])
    
    # Get mapped images
    mapping_df = pd.read_csv(MAPPING_FILE)
    mapped_files = set(mapping_df['image_filename'].dropna().str.strip())
    
    # Find unmapped
    unmapped = image_files - mapped_files
    
    if unmapped:
        print(f"\nFound {len(unmapped)} unmapped images:")
        for img in sorted(unmapped):
            print(f"  - {img}")
    else:
        print("All images in the directory are mapped!")

def show_mapping_stats():
    """Display statistics about the current mapping"""
    if not os.path.exists(MAPPING_FILE):
        print(f"Mapping file doesn't exist: {MAPPING_FILE}")
        return
    
    mapping_df = pd.read_csv(MAPPING_FILE)
    
    total_events = len(mapping_df)
    mapped_events = mapping_df['image_filename'].notna().sum()
    unmapped_events = total_events - mapped_events
    
    print(f"\nMapping Statistics:")
    print(f"  Total events: {total_events}")
    print(f"  Mapped (have images): {mapped_events}")
    print(f"  Unmapped (no images): {unmapped_events}")
    print(f"  Coverage: {mapped_events/total_events*100:.1f}%")
    
    if unmapped_events > 0:
        print(f"\nEvents without images:")
        unmapped = mapping_df[mapping_df['image_filename'].isna()]['event_title']
        for title in unmapped.head(10):
            print(f"  - {title}")
        if len(unmapped) > 10:
            print(f"  ... and {len(unmapped) - 10} more")

if __name__ == "__main__":
    import sys
    
    print("Event Image Mapping Tool")
    print("=" * 60)
    
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  1. Setup: python manual_image_mapper.py setup <events.csv>")
        print("  2. Apply:  python manual_image_mapper.py apply <events.csv> [output.csv]")
        print("  3. Stats:  python manual_image_mapper.py stats")
        print("  4. Check:  python manual_image_mapper.py check")
        print("\nExample workflow:")
        print("  1. python manual_image_mapper.py setup output/pipeline/calendar_upload.csv")
        print("  2. [Supervisor adds images to data/event_images/]")
        print("  3. [Edit data/event_image_mapping.csv to map images]")
        print("  4. python manual_image_mapper.py apply output/pipeline/calendar_upload.csv")
        print("  5. Upload the new CSV with images!")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "setup":
        if len(sys.argv) < 3:
            print("Error: Provide events CSV path")
            sys.exit(1)
        create_images_directory()
        create_mapping_template(sys.argv[2])
    
    elif command == "apply":
        if len(sys.argv) < 3:
            print("Error: Provide events CSV path")
            sys.exit(1)
        output = sys.argv[3] if len(sys.argv) > 3 else None
        apply_image_mapping(sys.argv[2], output)
    
    elif command == "stats":
        show_mapping_stats()
    
    elif command == "check":
        list_unmapped_images()
    
    else:
        print(f"Unknown command: {command}")
        print("Use: setup, apply, stats, or check")
        sys.exit(1)
