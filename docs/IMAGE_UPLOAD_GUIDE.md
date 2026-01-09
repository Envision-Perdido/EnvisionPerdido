# Event Image Upload Guide

## Overview

The pipeline now automatically extracts and uploads event images from the Perdido Chamber website to your WordPress calendar.

## How It Works

### 1. Image Extraction (Scraper)

When scraping events, the system now:
- Visits each event detail page
- Extracts the main event image using multiple methods:
  - Open Graph image meta tag (social media preview)
  - Common event image CSS selectors
  - First reasonably-sized image on the page
- Adds the `image_url` column to the CSV export

### 2. Image Upload (WordPress Uploader)

When uploading events to WordPress:
- Checks if the event has an `image_url` field
- Downloads the image from the chamber website
- Uploads it to WordPress media library
- Sets it as the event's featured image

## Using Images

### Automatic (Default)

Just run the pipeline as normal:
```powershell
.\scripts\windows\run_pipeline.ps1
```

Images will be automatically:
1. Scraped from event pages
2. Included in the CSV export
3. Uploaded to WordPress
4. Set as featured images

### Manual Image URLs

You can also manually specify image URLs in your CSV:

```csv
title,start,end,location,url,description,image_url
"Concert",2025-12-15T19:00:00,2025-12-15T21:00:00,"Music Hall","https://example.com/event","Live music","https://example.com/concert.jpg"
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
