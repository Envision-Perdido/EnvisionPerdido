# Manual Image Management Workflow

## Overview

When your supervisor provides custom images for events, use this workflow to map them to events before upload.

## Quick Start

### 1. Setup Image Directory

```powershell
cd C:\Users\scott\UWF-Code\EnvisionPerdido
python scripts/manual_image_mapper.py setup output/pipeline/calendar_upload_YYYYMMDD_HHMMSS.csv
```

This creates:
- `data/event_images/` directory for storing images
- `data/event_image_mapping.csv` template with all event titles

### 2. Add Images

Have your supervisor place images in `data/event_images/`:

```
data/event_images/
  beach_concert.jpg
  trivia_night.png
  holiday_market.jpg
  ...
```

### 3. Map Images to Events

Edit `data/event_image_mapping.csv`:

```csv
event_title,image_filename,notes
"Team Trivia at Lillian's Pizza","trivia_night.png","Provided by supervisor"
"Beach Concert Series","beach_concert.jpg","Main promotional image"
"Holiday Market","holiday_market.jpg",""
"Weekly Yoga Class","","No image available"
```

**Tips:**
- Leave `image_filename` blank for events without images
- Use exact filenames (case-sensitive on some systems)
- Add notes to track image sources or versions

### 4. Apply Mapping

```powershell
python scripts/manual_image_mapper.py apply output/pipeline/calendar_upload_YYYYMMDD_HHMMSS.csv
```

This creates a new CSV with `image_url` column containing local file paths.

### 5. Upload Events

Upload the new CSV with images:

```powershell
# Using the uploader directly
python -c "
from scripts.wordpress_uploader import WordPressEventUploader
import os

uploader = WordPressEventUploader(
    site_url=os.getenv('WP_SITE_URL'),
    username=os.getenv('WP_USERNAME'),
    app_password=os.getenv('WP_APP_PASSWORD')
)

uploader.upload_events_from_csv(
    'output/pipeline/calendar_upload_YYYYMMDD_HHMMSS_with_images.csv',
    dry_run=False
)
"
```

## Commands Reference

### Setup
```powershell
python scripts/manual_image_mapper.py setup <events.csv>
```
Creates image directory and mapping template from events CSV.

### Apply Mapping
```powershell
python scripts/manual_image_mapper.py apply <events.csv> [output.csv]
```
Merges image mapping into events CSV. Output defaults to `<events>_with_images.csv`.

### Check Stats
```powershell
python scripts/manual_image_mapper.py stats
```
Shows how many events have images mapped.

### Find Unmapped Images
```powershell
python scripts/manual_image_mapper.py check
```
Lists image files that aren't assigned to any event.

## Workflow Examples

### One-Time Upload with Custom Images

```powershell
# 1. Run pipeline to get latest events (without images)
.\scripts\windows\run_pipeline.ps1

# 2. Setup mapping for the generated CSV
python scripts/manual_image_mapper.py setup output/pipeline/calendar_upload_20251204_153744.csv

# 3. Supervisor adds images to data/event_images/

# 4. Edit data/event_image_mapping.csv to map images

# 5. Apply mapping
python scripts/manual_image_mapper.py apply output/pipeline/calendar_upload_20251204_153744.csv

# 6. Upload the new CSV (events already published, so update them)
# Note: You'd need to delete existing events first or modify uploader to update
```

### Mixed Approach (Auto + Manual)

```powershell
# Scrape events with auto-detected images from chamber website
.\scripts\windows\run_pipeline.ps1

# Override specific events with supervisor's custom images
python scripts/manual_image_mapper.py setup output/pipeline/calendar_upload_LATEST.csv
# Edit mapping - only fill in events you want to override
python scripts/manual_image_mapper.py apply output/pipeline/calendar_upload_LATEST.csv

# Upload with mixed images (auto + manual overrides)
# The manual ones will take precedence
```

### Recurring Events with Same Images

If certain recurring events always use the same image:

1. Create a permanent mapping file for recurring events:
```csv
event_title,image_filename,notes
"Team Trivia at Lillian's Pizza","trivia_lillians.jpg","Standard trivia image"
"Music Bingo at Perdido Key Sports Bar","bingo_perdido.png","Standard bingo image"
```

2. Keep these images in `data/event_images/` permanently

3. Run apply mapping before each upload

## File Structure

```
EnvisionPerdido/
├── data/
│   ├── event_images/              ← Supervisor's images go here
│   │   ├── beach_concert.jpg
│   │   ├── trivia_night.png
│   │   └── ...
│   └── event_image_mapping.csv    ← Maps events to images
├── output/
│   └── pipeline/
│       ├── calendar_upload_YYYYMMDD_HHMMSS.csv           ← Original
│       └── calendar_upload_YYYYMMDD_HHMMSS_with_images.csv  ← With images
└── scripts/
    ├── manual_image_mapper.py     ← This tool
    └── wordpress_uploader.py      ← Uploads events with images
```

## Image Requirements

**Supported Formats:**
- JPEG (.jpg, .jpeg)
- PNG (.png)
- GIF (.gif)
- WebP (.webp)

**Recommended Specs:**
- Size: 800-1200px wide
- Aspect ratio: 16:9 or 4:3
- File size: < 2 MB
- Quality: High enough for web display

**Naming Convention:**
- Use descriptive names: `beach_concert_dec2025.jpg`
- Avoid spaces: use underscores or hyphens
- Keep it simple: lowercase preferred

## Troubleshooting

**"Image file not found" warnings:**
- Check filename spelling in mapping CSV
- Verify image is actually in `data/event_images/`
- Use absolute paths if relative paths aren't working

**Images not uploading to WordPress:**
- Check file size limits (WordPress default ~2-8 MB)
- Verify image format is supported
- Check WordPress media upload permissions
- Review upload logs for errors

**Wrong image attached to event:**
- Verify event title matches exactly in mapping CSV
- Check for duplicate event titles
- Use unique identifiers if titles repeat

**Mixed auto/manual images:**
The uploader prioritizes `image_url` column:
1. If event has `image_url` → uses that (manual override)
2. If no `image_url` → no image uploaded
3. Auto-scraped images are in the original CSV already

## Advanced: Batch Image Renaming

If supervisor sends images with generic names, rename them:

```powershell
# Example: Rename based on mapping
$mapping = Import-Csv data/event_image_mapping.csv
foreach ($row in $mapping) {
    $old = "data/event_images/$($row.old_filename)"
    $new = "data/event_images/$($row.image_filename)"
    if (Test-Path $old) {
        Rename-Item $old $new
        Write-Host "Renamed: $old -> $new"
    }
}
```

## Integration with Automated Pipeline

To integrate manual images into automated runs, add a step after classification:

```python
# In automated_pipeline.py, after exporting CSV but before upload:

# Check if manual image mapping exists
if os.path.exists('data/event_image_mapping.csv'):
    log("Applying manual image mapping...")
    from manual_image_mapper import apply_image_mapping
    df = apply_image_mapping(export_path, export_path)
    log(f"Applied manual images to {df['image_url'].notna().sum()} events")
```

This way supervisor's images are automatically used when available, falling back to auto-scraped images otherwise.
