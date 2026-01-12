Live tests and running against a real WordPress site

Summary
-------
This project includes a (small) live integration test that will contact a WordPress site and perform GET/POST operations.

Safety-first defaults
---------------------
- Live-site tests are skipped by default to avoid accidental network calls or modifications.
- To enable them intentionally set the environment variable:

  RUN_LIVE_SITE_TESTS=1

Credentials
-----------
The test looks for WP credentials in this order:

1) Environment variables: WP_SITE_URL, WP_USERNAME, WP_APP_PASSWORD
2) A local secrets file (recommended): ~/.secrets/envision_env.ps1
   - This file should contain PowerShell-style lines such as:
     $env:WP_SITE_URL = "https://your-site"
     $env:WP_USERNAME = "youruser"
     $env:WP_APP_PASSWORD = "your-app-password"
3) Fallback to scripts/windows/env.ps1 if present (not recommended for production secrets)

Important security notes
------------------------
- Never commit real credentials into the repository. Add any local secrets file paths to your personal gitignore if needed.
- Prefer using a staging/test WordPress instance or a limited-scope application password for live tests.

How to run the live test manually
--------------------------------
# 1) Set up credentials in environment variables (example)
export WP_SITE_URL="https://your-site"
export WP_USERNAME="user"
export WP_APP_PASSWORD="app-password"

# 2) Run the test (this will perform a GET and a POST on the site)
RUN_LIVE_SITE_TESTS=1 ~/.virtualenvs/envisionperdido/bin/python scripts/test_hour_format.py

Alternative: use a local secrets file
-------------------------------------
# create ~/.secrets/envision_env.ps1 with PowerShell lines as shown above
RUN_LIVE_SITE_TESTS=1 ~/.virtualenvs/envisionperdido/bin/python scripts/test_hour_format.py

If you want me to add a `pytest` marker (e.g., @pytest.mark.live) instead of the module-level skip, I can implement that and update CI accordingly.
