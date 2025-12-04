import os, requests
from requests.auth import HTTPBasicAuth

site = os.getenv('WP_SITE_URL', '').rstrip('/')
auth = HTTPBasicAuth(os.getenv('WP_USERNAME', ''), os.getenv('WP_APP_PASSWORD', ''))

# Get an event with ALL its meta
r = requests.get(f'{site}/wp-json/wp/v2/ajde_events', params={'per_page': 1}, auth=auth, timeout=20)
if r.status_code == 200 and r.json():
    event = r.json()[0]
    meta = event.get('meta', {})
    
    print('Event:', event.get('title', {}).get('rendered', ''))
    print('\nALL Meta Fields:')
    for key in sorted(meta.keys()):
        value = meta[key]
        # Truncate long values
        if isinstance(value, str) and len(value) > 100:
            value = value[:100] + '...'
        print(f'  {key}: {value}')
else:
    print('Error:', r.status_code)
