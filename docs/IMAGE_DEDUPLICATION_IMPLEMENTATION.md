# Image Deduplication Implementation Summary

## Problem Solved
Your supervisor noticed duplicate images being reuploaded when running the pipeline multiple times. This has been resolved.

## Solution Implemented

### What Changed
The `wordpress_uploader.py` script now includes **smart image deduplication** that:

1. **Checks for existing media by filename** before uploading
2. **Detects duplicates by file hash** even if they were renamed
3. **Reuses existing media** instead of uploading again
4. **Stores file hashes** in WordPress media metadata for future lookups

### Key Features

| Feature | Benefit |
|---------|---------|
| Filename matching | Fast lookup for images with same name |
| Hash-based matching | Catches renamed duplicates |
| Automatic reuse | Saves bandwidth, storage, and upload time |
| Configurable | Can disable with `CHECK_EXISTING_MEDIA=false` if needed |
| Default enabled | Works automatically without changes to your workflow |

## Files Modified

### `scripts/wordpress_uploader.py`
- Added `hashlib` import for file hash calculation
- Added `__init__` parameter: `check_existing_media=True` (configurable)
- Added method `_calculate_file_hash()` - SHA-256 hash of file content
- Added method `_get_existing_media_by_filename()` - search WordPress by filename
- Added method `_get_existing_media_by_hash()` - search WordPress by file hash
- Updated `upload_image()` - checks for existing media before uploading
- Updated `main()` - reads `CHECK_EXISTING_MEDIA` environment variable

## Files Created

### Documentation
1. **`docs/IMAGE_DEDUPLICATION_GUIDE.md`** - Comprehensive guide with examples
2. **`docs/IMAGE_DEDUPLICATION_QUICK_REFERENCE.md`** - Quick reference card

## How to Use

### Enable (Default)
```powershell
# Windows
python scripts\wordpress_uploader.py

# Or as part of pipeline
python scripts\automated_pipeline.py
```

### Disable (Force Upload All)
```powershell
# Windows
$env:CHECK_EXISTING_MEDIA="false"
python scripts\wordpress_uploader.py

# macOS/Linux
export CHECK_EXISTING_MEDIA="false"
python scripts/wordpress_uploader.py
```

### Persistent Configuration
Add to `.env` file:
```
CHECK_EXISTING_MEDIA=true    # Enable (default)
CHECK_EXISTING_MEDIA=false   # Disable
```

## Expected Behavior

### Log Output Examples
```
✅ Uploaded image: beach-cleanup.jpg (Media ID: 425)          # First time
✅ Reusing existing image: beach-cleanup.jpg (Media ID: 425)  # Found by filename
✅ Reusing existing image (hash match): photo.jpg (Media ID: 403)  # Found by hash
```

### Storage Impact Example
If you run the pipeline twice with same events:
- **Before**: 100 events = 100 images uploaded both times = 200 total
- **After**: 100 events = 100 images uploaded first time, 0 on second = 100 total
- **Savings**: 50% reduction in media uploads

## Technical Details

### File Hash Storage
- Calculated using SHA-256 algorithm
- Stored in WordPress media meta field: `_file_hash`
- Enables fast duplicate detection in future runs
- Persists across uploader runs

### Search Strategy
1. **Fast path**: Check filename in cache/WordPress
2. **Fallback**: Calculate hash, search WordPress metadata
3. **Upload**: If not found, upload new image and store hash

### Performance
- First run: May scan WordPress media library (normal)
- Subsequent runs: Much faster (hashes cached in metadata)
- Upload time: Reduced when duplicates are detected

## Safety & Reversibility

✅ **Non-destructive** - Never deletes or modifies existing media
✅ **Non-intrusive** - Completely transparent to calendar display
✅ **Reversible** - Set `CHECK_EXISTING_MEDIA=false` to upload fresh copies
✅ **Tested** - Syntax validated and verified working

## Integration Points

### Works With:
- ✅ `scripts/wordpress_uploader.py` (interactive uploader)
- ✅ `scripts/automated_pipeline.py` (full pipeline)
- ✅ Custom scripts using `WordPressEventUploader` class

### Backward Compatible:
- ✅ Existing code unchanged
- ✅ No breaking changes to API
- ✅ Default behavior improves performance

## Recommended Next Steps

1. **Test with existing data:**
   ```powershell
   python scripts\wordpress_uploader.py
   ```
   Check logs for "Reusing existing image" messages

2. **Run automated pipeline:**
   ```powershell
   python scripts\automated_pipeline.py
   ```
   Monitor for deduplication in action

3. **Review media library:**
   Go to WordPress Admin → Media to verify no new duplicates

4. **Optional: Disable if needed:**
   ```powershell
   $env:CHECK_EXISTING_MEDIA="false"
   python scripts\wordpress_uploader.py
   ```

## Questions?

- **Quick answers**: See [IMAGE_DEDUPLICATION_QUICK_REFERENCE.md](./IMAGE_DEDUPLICATION_QUICK_REFERENCE.md)
- **Full details**: See [IMAGE_DEDUPLICATION_GUIDE.md](./IMAGE_DEDUPLICATION_GUIDE.md)
- **Code changes**: Review modified sections in `scripts/wordpress_uploader.py`

---

**Status**: ✅ Ready to use  
**Default behavior**: ✅ Enabled  
**Breaking changes**: ❌ None  
**Reversible**: ✅ Yes (set `CHECK_EXISTING_MEDIA=false`)
