import os, requests
from requests.auth import HTTPBasicAuth
from datetime import datetime
from zoneinfo import ZoneInfo

site = os.getenv('WP_SITE_URL', '').rstrip('/')
auth = HTTPBasicAuth(os.getenv('WP_USERNAME', ''), os.getenv('WP_APP_PASSWORD', ''))

r = requests.get(f'{site}/wp-json/wp/v2/ajde_events', params={'per_page': 1}, auth=auth, timeout=20)
if r.status_code == 200 and r.json():
    event = r.json()[0]
    meta = event.get('meta', {})
    print('Event:', event.get('title', {}).get('rendered', ''))
    print('\nStored Meta:')
    print(f"  evcal_srow: {meta.get('evcal_srow')}")
    print(f"  evcal_start_date: {meta.get('evcal_start_date')}")
    print(f"  evcal_start_time_hour: {meta.get('evcal_start_time_hour')}")
    print(f"  evcal_start_time_min: {meta.get('evcal_start_time_min')}")
    print(f"  evcal_start_time_ampm: {meta.get('evcal_start_time_ampm')}")
    
    epoch = int(meta.get('evcal_srow', 0))
    utc_dt = datetime.fromtimestamp(epoch, tz=ZoneInfo('UTC'))
    cst_dt = utc_dt.astimezone(ZoneInfo('America/Chicago'))
    print(f'\nEpoch {epoch}:')
    print(f'  UTC: {utc_dt.strftime("%Y-%m-%d %I:%M %p")}')
    print(f'  CST: {cst_dt.strftime("%Y-%m-%d %I:%M %p")}')
else:
    print('Error fetching event:', r.status_code)
