# Event Image Upload Guide

## Overview

The pipeline supports TWO ways to add images to events:

1. **Automatic Scraping** — Download images from chamber website (optional)
2. **Manual Mapping** — Use supervisor-provided images (NEW!)

## Method 1: Automatic Image Scraping (From Website)

When scraping events, the system can extract images from the chamber website.

### How It Works

The scraper:
- Visits each event detail page
- Extracts the main event image using:
  - Open Graph meta tags (social media preview)
  - CSS image selectors
  - First reasonably-sized image on page
- Adds `image_url` column to CSV export

### Usage

Just run the pipeline as normal:
```powershell
python scripts/run_pipeline_with_smoketest.py
```

Images will be:
1. Automatically extracted during scraping
2. Included in CSV export
3. Uploaded to WordPress during uploader phase
4. Set as event featured images

---

## Method 2: Manual Image Mapping (NEW!)

Use your supervisor's approved images instead of scraped images.

### Setup (One Time)

```powershell
# Initialize image directories
python scripts/setup_image_mapper.py init

# Create mapping template from latest events
python scripts/setup_image_mapper.py create-template
```

### Steps

**1. Place Images**
- Copy your supervisor's images to: `data/event_images/`
- Supported formats: JPG, PNG, GIF, WebP

**2. Edit Mapping**
- Open: `data/event_image_mapping.csv`
- Fill in `image_filename` column:

```csv
event_title,image_filename,notes
Brandon Styles VARIETY SHOW,brandon_styles.jpg,Provided by supervisor
Buzz Runners,buzz_runners.png,Artist headshot
Concert 2026,concert_2026.jpg,Event promotion image
```

**3. Run Pipeline**
```powershell
python scripts/run_pipeline_with_smoketest.py
```

The pipeline automatically:
- Detects image mappings
- Applies them to events
- Includes in CSV export

**4. Upload to WordPress**
```powershell
python scripts/wordpress_uploader.py output/pipeline/calendar_upload_*.csv
```

### Check Status

```powershell
# See image statistics
python scripts/setup_image_mapper.py stats

# Verify all images exist
python scripts/setup_image_mapper.py verify
```

The uploader supports:
- **Remote URLs**: Downloads and uploads the image
- **Local file paths**: Reads and uploads the file
- **Missing images**: Skips upload if no image provided

### Disable Image Upload

To upload events without images, you can:

**Option 1**: Remove the `image_url` column from your CSV

**Option 2**: Modify the uploader call in `automated_pipeline.py`:
```python
# Instead of:
uploader.upload_events_from_csv(csv_path, dry_run=False)

# Use:
for idx, row in df.iterrows():
    uploader.create_event(row, image_column=None)  # Disable images
```

## Technical Details

### Supported Image Formats
- JPEG/JPG
- PNG
- GIF
- WebP
- Any format WordPress supports

### Image Selection Logic

The scraper tries multiple methods to find the best image:

1. **Open Graph tag** (`<meta property="og:image">`) - Most reliable
2. **CSS selectors** - Common event image classes
3. **Size filtering** - Skips icons, logos, and tiny images
4. **Fallback** - First image meeting minimum size requirements

### Troubleshooting

**Images not appearing on calendar**:
1. Check CSV has `image_url` column populated
2. Verify image URLs are accessible
3. Check WordPress upload permissions
4. Review pipeline logs for upload errors

**Wrong image selected**:
- The scraper picks the first "event-sized" image it finds
- You can manually edit the CSV to specify the correct URL
- Adjust `get_event_image_url()` function in scraper if needed

**Upload failures**:
- Ensure WordPress has sufficient media storage space
- Check file size limits in WordPress settings
- Verify image URLs are publicly accessible
- Check for SSL/certificate issues with image hosts

## Configuration

### Image Column Name

Default column: `image_url`

To use a different column name:
```python
uploader.create_event(event_row, image_column='my_image_field')
```

### Image Size Limits

WordPress default limits apply:
- Max file size: Usually 2-8 MB (server dependent)
- Max dimensions: Usually unlimited but recommended < 2000px

The uploader does NOT resize images - they're uploaded as-is.

## Future Enhancements

Potential improvements:
- Image caching to avoid re-downloading
- Image resizing/optimization before upload
- Support for multiple images per event
- Image validation (check dimensions, format, size)
- Retry logic for failed downloads
- Custom image selection preferences

## Examples

### Full Pipeline with Images

```powershell
# Run complete pipeline (scrape + classify + upload with images)
.\scripts\windows\run_pipeline.ps1
```

### Upload Existing CSV with Images

```python
from wordpress_uploader import WordPressEventUploader

uploader = WordPressEventUploader(
    site_url="https://sandbox.envisionperdido.org",
    username="your_username",
    app_password="your_app_password"
)

# Upload events with images
uploader.upload_events_from_csv("events.csv", dry_run=False)
```

### Upload Single Event with Image

```python
import pandas as pd

event = {
    'title': 'Beach Cleanup',
    'start': '2025-12-20T09:00:00',
    'end': '2025-12-20T12:00:00',
    'location': 'Perdido Key Beach',
    'image_url': 'https://example.com/beach.jpg'
}

event_id = uploader.create_event(pd.Series(event))
uploader.publish_events([event_id])
```
