# Image Deduplication - Quick Reference

## TL;DR

**Duplicate images are no longer reuploaded.** The system now:
1. Checks if the image already exists on WordPress (by filename)
2. If not found, checks by file hash (catches renamed duplicates)
3. Reuses existing media instead of uploading

## Enable/Disable

**Enable (default):**
```powershell
# Windows
python scripts\wordpress_uploader.py

# macOS/Linux
python scripts/wordpress_uploader.py
```

**Disable (force upload all images):**
```powershell
# Windows
$env:CHECK_EXISTING_MEDIA="false"
python scripts\wordpress_uploader.py

# macOS/Linux
export CHECK_EXISTING_MEDIA="false"
python scripts/wordpress_uploader.py
```

## What You'll See in Logs

```
✅ Uploaded image: beach.jpg (Media ID: 425)        # NEW
✅ Reusing existing image: park.png (Media ID: 418) # REUSED
✅ Reusing existing image (hash match): photo.jpg (Media ID: 403) # REUSED (renamed)
```

## Storage Impact

- **Before**: 100 events × 3 uploads = 300 images stored
- **After**: 100 events × 2 unique images = 200 images stored
- **Savings**: ~33% less storage per run

## Configuration in `.env`

```
# Enable (default)
CHECK_EXISTING_MEDIA=true

# Disable
CHECK_EXISTING_MEDIA=false
```

---

**Questions?** See [IMAGE_DEDUPLICATION_GUIDE.md](./IMAGE_DEDUPLICATION_GUIDE.md) for full details.
