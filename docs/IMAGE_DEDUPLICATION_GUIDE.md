# Image Deduplication Guide

## Overview

To prevent duplicate images from being reuploaded to WordPress, the uploader now includes **smart image deduplication** that checks for existing media before uploading.

## How It Works

### 1. **Filename Matching**
   - First, checks if an image with the same filename already exists on WordPress
   - Quick lookup using WordPress media library search

### 2. **Hash-Based Matching** (Fallback)
   - If filename doesn't match, calculates a SHA-256 hash of the image file
   - Searches WordPress for existing images with the same hash
   - **Detects duplicate images even if they were renamed**

### 3. **Reuse Existing Media**
   - If a match is found, reuses that media instead of uploading
   - Saves bandwidth and storage space
   - Reduces upload time significantly

## Enabling/Disabling Deduplication

### Default Behavior
Image deduplication is **ENABLED by default** when running the uploader.

### To Disable (Force Fresh Uploads)
If you need to upload all images even if they already exist on WordPress:

#### **Windows PowerShell:**
```powershell
$env:CHECK_EXISTING_MEDIA="false"
python scripts\wordpress_uploader.py
```

#### **macOS/Linux (zsh/bash):**
```bash
export CHECK_EXISTING_MEDIA="false"
python scripts/wordpress_uploader.py
```

#### **Persistent Setting** (Add to `.env`)
```
CHECK_EXISTING_MEDIA=false
```

## Example: Duplicate Detection in Action

### Scenario
You've already uploaded 50 events with images. Now you're adding 10 new events, but 3 of them happen to use images from the previous batch (same URLs).

### What Happens

**Without deduplication (old behavior):**
```
Uploading 10 events:
  [1/10] Uploaded image: beach-cleanup-1.jpg (Media ID: 425)
  [2/10] Uploaded image: park-event.jpg (Media ID: 426)
  [3/10] Uploaded image: beach-cleanup-1.jpg (Media ID: 427)  ← DUPLICATE!
  [4/10] Uploaded image: community-garden.jpg (Media ID: 428)
  ...
Result: 10 new images uploaded, 3 are exact duplicates
```

**With deduplication (new behavior):**
```
Uploading 10 events:
  [1/10] Uploaded image: beach-cleanup-1.jpg (Media ID: 425)
  [2/10] Uploaded image: park-event.jpg (Media ID: 426)
  [3/10] Reusing existing image: beach-cleanup-1.jpg (Media ID: 425)  ← REUSED!
  [4/10] Uploaded image: community-garden.jpg (Media ID: 428)
  ...
Result: 7 new images uploaded, 3 reused existing media
```

## Viewing Results in Logs

When you run the uploader, look for these messages:

```
[2026-02-05 10:15:32] Uploaded image: event_photo.jpg (Media ID: 425)     ← NEW UPLOAD
[2026-02-05 10:15:33] Reusing existing image: banner.png (Media ID: 418)  ← REUSED
[2026-02-05 10:15:34] Reusing existing image (hash match): photo.jpg (Media ID: 403)  ← SAME FILE, DIFFERENT NAME
```

## How Deduplication Gets Better Over Time

The system stores a **file hash** (`_file_hash` meta field) on each uploaded image in WordPress. This means:

1. **First run:** Uses filename matching + does a full media scan for hashes
2. **Subsequent runs:** Much faster because hashes are already stored in media metadata
3. **Different filenames:** Even if the same image is uploaded with different names, it's detected as a duplicate

## Technical Details

### File Hash Storage
When an image is uploaded:
- A SHA-256 hash of the file is calculated
- Hash is stored in WordPress media meta field: `_file_hash`
- Hash is used in subsequent uploads for fast duplicate detection

### Caching
The uploader caches filename lookups during a single run to speed up processing. Cache is cleared between runs.

## Integration with Automated Pipeline

If using `scripts/automated_pipeline.py`, image deduplication works automatically:

```bash
# Deduplication enabled by default
python scripts/automated_pipeline.py

# To disable (force all images to upload):
export CHECK_EXISTING_MEDIA="false"
python scripts/automated_pipeline.py
```

## Troubleshooting

### Images Not Reusing (Always Uploading New)

**Check if feature is enabled:**
```powershell
# Windows
$env:CHECK_EXISTING_MEDIA
# Should print: true

# macOS/Linux
echo $CHECK_EXISTING_MEDIA
# Should print: true
```

**If disabled, enable it:**
```powershell
# Windows
$env:CHECK_EXISTING_MEDIA="true"

# macOS/Linux
export CHECK_EXISTING_MEDIA="true"
```

### Duplicate Still Appearing

1. Clear `CHECK_EXISTING_MEDIA` to force a fresh check
2. Verify WordPress media library for duplicates manually
3. Check logs for hash calculation errors

### Performance Issues

If upload is slow with many images:
- Deduplication may be running a full scan of WordPress media
- This is normal on first run with large media libraries
- Subsequent runs are faster due to meta field caching

## FAQ

**Q: Does this affect how images display on the calendar?**  
A: No. Image deduplication is transparent to the calendar display. Events still show the correct images.

**Q: What if I accidentally delete an image from WordPress?**  
A: The next upload will detect it's missing and upload a fresh copy. No intervention needed.

**Q: Can I check existing media for specific events only?**  
A: Not yet, but you can manually manage media in WordPress admin if needed.

**Q: Does hash matching slow down uploads?**  
A: On first run, yes—it needs to scan the WordPress media library once. Subsequent runs are faster.

---

## For Administrators

### Quick Summary for Your Supervisor

✅ **Before**: Every pipeline run uploaded all images → duplicates accumulated  
✅ **After**: Pipeline checks WordPress before uploading → reuses existing media  
✅ **Result**: Faster uploads, less storage used, cleaner media library  

The feature is enabled by default but can be disabled with `CHECK_EXISTING_MEDIA=false` if needed.
