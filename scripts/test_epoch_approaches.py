from datetime import datetime
from zoneinfo import ZoneInfo

# Event time from CSV: 7 PM on Dec 1 (already in local time)
local_time = datetime(2025, 12, 1, 19, 0, 0)  # 7 PM
print("Local time (from CSV): 2025-12-01 19:00:00")

# Approach 1: Treat as local, convert to UTC for epoch (what we're doing now)
cst = ZoneInfo("America/Chicago")
local_tz = local_time.replace(tzinfo=cst)
utc_epoch = int(local_tz.astimezone(ZoneInfo("UTC")).timestamp())
print(f"\nApproach 1 (UTC epoch): {utc_epoch}")

# Approach 2: Treat as local and use local epoch directly
local_epoch = int(local_time.timestamp())
print(f"Approach 2 (local epoch): {local_epoch}")

# Verify what each epoch shows
print("\nVerify:")
from_utc = datetime.fromtimestamp(utc_epoch, tz=ZoneInfo("UTC")).astimezone(
    ZoneInfo("America/Chicago")
)
from_local = datetime.fromtimestamp(local_epoch, tz=ZoneInfo("America/Chicago"))

print(f"Approach 1 converts back to: {from_utc.strftime('%Y-%m-%d %I:%M %p')} (should be 7:00 PM)")
print(
    f"Approach 2 converts back to: {from_local.strftime('%Y-%m-%d %I:%M %p')} (should be 7:00 PM)"
)
