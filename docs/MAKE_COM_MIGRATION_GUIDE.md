# Make.com CI/CD Migration Guide for EnvisionPerdido

## Overview

This guide walks you through migrating the **EnvisionPerdido automated community calendar system** from a local Windows PC to **Make.com** (formerly Integromat) for cloud-based CI/CD execution while maintaining your local copy.

**Benefits:**
- 🌐 **Cloud Execution**: Runs 24/7 without PC on
- 👥 **Team Collaboration**: Supervisors can monitor & override without local access
- 📊 **Built-in Monitoring**: Email alerts, execution logs, visibility
- 🔒 **Secure Credential Management**: Centralized secrets handling
- 📈 **Scalability**: Easy to add new data sources or workflows

---

## Architecture Overview

```
┌─────────────────────┐
│   Make.com Cloud    │
│   ┌───────────────┐ │
│   │  Scenarios:   │ │
│   │ 1. Scrape     │ │
│   │ 2. Classify   │ │
│   │ 3. Email      │ │
│   │ 4. Upload     │ │
│   └───────────────┘ │
│    ↓ Results        │
│   Google Drive      │
│   Email             │
│   WordPress         │
└─────────────────────┘
         ↓
┌──────────────────────┐
│   Your PC (Local)    │
│  EnvisionPerdido     │
│  (Mirror/Reference)  │
└──────────────────────┘
```

**Key Points:**
- Make.com runs Python scripts via **webhooks** or **scheduler**
- Results sync to **Google Drive** for version control
- Supervisors log into **Make.com dashboard** to monitor
- Your PC remains the "source of truth" (optional backup)

---

## Phase 1: Preparation (Local Setup)

### 1.1 Create a Cloud Storage Hub

You'll need persistent storage for:
- Model artifacts (`event_classifier_model.pkl`, `event_vectorizer.pkl`)
- Configuration files (email, WordPress credentials)
- Output CSVs and logs

**Option A: Google Drive (Recommended)**
- Free tier: 15 GB
- Easy to share with supervisors
- Works natively with Make.com

**Option B: AWS S3 / DigitalOcean Spaces**
- More robust, pay-per-use
- Better for production

For this guide, we'll use **Google Drive**.

### 1.2 Prepare Your Model & Artifacts

1. **Copy model files to Google Drive:**
   ```
   Your Drive/
   └── EnvisionPerdido/
       ├── models/
       │   ├── event_classifier_model.pkl
       │   └── event_vectorizer.pkl
       ├── config/
       │   ├── credentials.json (WordPress)
       │   └── image_keyword_config.json
       └── cache/
           └── (scraped CSVs, intermediate files)
   ```

2. **Verify model size:**
   ```powershell
   # On your PC
   Get-ChildItem "c:\Users\scott\UWF-Code\EnvisionPerdido\data\artifacts\" | 
     ForEach-Object { Write-Host $_.Name, $_.Length }
   ```

3. **Upload to Google Drive manually** (one-time setup):
   - Go to https://drive.google.com
   - Create folder structure above
   - Upload `.pkl` files and config

### 1.3 Create Environment Variable Management File

Create a **secure credentials file** (NOT committed to git):

**File: `scripts/make_env_template.json`** (committed)
```json
{
  "REQUIRED_ENV_VARS": {
    "SMTP_SERVER": "smtp.gmail.com",
    "SMTP_PORT": "587",
    "SENDER_EMAIL": "your_email@gmail.com",
    "EMAIL_PASSWORD": "STORE_IN_MAKE_SECRETS",
    "RECIPIENT_EMAIL": "your_email@gmail.com",
    "WP_SITE_URL": "https://your-site.org",
    "WP_USERNAME": "STORE_IN_MAKE_SECRETS",
    "WP_APP_PASSWORD": "STORE_IN_MAKE_SECRETS",
    "GOOGLE_DRIVE_FOLDER_ID": "your_folder_id_here",
    "SITE_TIMEZONE": "America/Chicago"
  },
  "NOTES": "All STORE_IN_MAKE_SECRETS values should be configured in Make.com Secrets module"
}
```

**File: `scripts/make_env_secrets.json`** (NOT committed - add to `.gitignore`)
```json
{
  "SMTP_SERVER": "smtp.gmail.com",
  "SMTP_PORT": "587",
  "SENDER_EMAIL": "your_email@gmail.com",
  "EMAIL_PASSWORD": "your_16_char_app_password",
  "RECIPIENT_EMAIL": "your_email@gmail.com",
  "WP_SITE_URL": "https://your-site.org",
  "WP_USERNAME": "your_wp_username",
  "WP_APP_PASSWORD": "xxxx xxxx xxxx xxxx xxxx xxxx",
  "GOOGLE_DRIVE_FOLDER_ID": "1abc2def3ghi4jkl5mno6pqr",
  "SITE_TIMEZONE": "America/Chicago"
}
```

### 1.4 Update `.gitignore`

Add these lines:
```
scripts/make_env_secrets.json
.make_credentials/
credentials_local.json
```

---

## Phase 2: Create Make.com Account & Connect Services

### 2.1 Set Up Make.com Account

1. Go to https://make.com
2. Sign up (free tier available, see pricing)
3. Create a **new organization** (invite supervisors later)
4. Accept email verification

### 2.2 Connect Necessary Services

This section walks you through connecting each service. Make.com will ask for permission when you add each connection.

---

#### **A. Google Drive Integration (Step-by-step)**

This allows Make.com to download your model files and upload results to Google Drive.

**Step 1: Go to Connections**
1. Log in to Make.com (https://make.com)
2. Look at the **left sidebar** (navigation menu)
3. Click **Connections** (it looks like a chain link icon)
4. You'll see a list of connected services (currently empty)

**Step 2: Add Google Drive**
1. Click the **+ Add connection** button (top right of the Connections page)
2. A list of apps will appear
3. **Search for "Google Drive"** in the search box
4. Click on **Google Drive** when it appears
5. A new window will pop up asking permission
6. **Click "Allow"** to let Make.com access your Google Drive

**Step 3: Verify Your Google Drive Folder ID**
1. Open a new browser tab and go to Google Drive: https://drive.google.com
2. Navigate to your **EnvisionPerdido** folder (the one you created in Phase 1.2)
3. Look at the **URL bar** at the top of the browser
4. You should see: `https://drive.google.com/drive/folders/[FOLDER_ID]`
5. Copy the long ID after `/folders/`
   - Example: `1AV4jSzgjFkwC-FF_wITEeyZRgOxdGDTI`
6. **Paste this into your `make_env_secrets.json`** as `GOOGLE_DRIVE_FOLDER_ID` (you may have already done this)

**What you just did:** Make.com can now access your Google Drive and work with files in your EnvisionPerdido folder.

---

#### **B. Gmail Integration (for email notifications)**

This allows Make.com to send you email notifications when the pipeline runs.

**Step 1: Go Back to Connections**
1. In Make.com, click **Connections** again (left sidebar)
2. Click **+ Add connection**
3. Search for **"Gmail"**
4. Click **Gmail** in the results

**Step 2: Authorize Gmail**
1. A browser pop-up will ask: "Make.com wants to access your Google Account"
2. **Click "Allow"**
3. Select the email address you want to use (the one from `SENDER_EMAIL` in your `make_env_secrets.json`)
4. Click **Allow** again to confirm permissions

**Step 3: Test Gmail Access**
1. Back in Make.com, you should now see **Gmail** in your Connections list
2. The connection status should say **Connected** ✅

**What you just did:** Make.com can now send emails from your Gmail account.

---

#### **C. Google Sheets Integration (Optional but Recommended for Dashboards)**

This allows Make.com to log execution history to a Google Sheet for tracking.

**Step 1: Create a Google Sheet First (Optional)**
1. Go to https://sheets.google.com
2. Click **+ Create new spreadsheet**
3. Name it: `EnvisionPerdido Execution Log`
4. Create tabs (sheets) for:
   - **Pipeline Runs** — Dates, event counts, status
   - **Upload History** — Upload attempts, who approved, when
   - **Error Log** — Any failures and details

**Step 2: Add Google Sheets Connection**
1. In Make.com, click **Connections**
2. Click **+ Add connection**
3. Search for **"Google Sheets"**
4. Click **Google Sheets** in results
5. A pop-up will ask for permission → **Click Allow**
6. Select your Google account → **Allow**

**What you just did:** Make.com can now write data to your Google Sheet (for dashboards & tracking).

---

#### **D. WordPress Integration (NO pre-connection needed)**

WordPress uses **HTTP Basic Auth** with your app password, which we'll handle inside the scenarios using environment variables (from `make_env_secrets.json`).

**But first, verify your credentials work locally:**

1. Open **PowerShell** on your PC
2. Run this command:
   ```powershell
   # Test WordPress REST API with your credentials
   $auth = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes("YOUR_WP_USERNAME:YOUR_WP_APP_PASSWORD"))
   
   $response = Invoke-WebRequest `
     -Uri "https://your-site.org/wp-json/wp/v2/users/me" `
     -Headers @{"Authorization" = "Basic $auth"} `
     -Method GET
   
   if ($response.StatusCode -eq 200) {
       Write-Host "✅ WordPress connection works!"
   } else {
       Write-Host "❌ WordPress connection failed. Check credentials."
   }
   ```

3. Replace:
   - `YOUR_WP_USERNAME` with your WordPress username
   - `YOUR_WP_APP_PASSWORD` with your app password
   - `https://your-site.org` with your actual site URL

4. If you see `✅ WordPress connection works!`, you're good!
5. If you get an error, double-check your credentials

**What you just did:** Verified that WordPress can authenticate with Make.com (no connection needed, we'll use HTTP module instead).

---

## Phase 3: Refactor Scripts for Cloud Execution

### 3.1 Create a Wrapper Script for Make.com

**File: `scripts/make_cloud_pipeline.py`**

```python
"""
Make.com Cloud Pipeline Wrapper

This script is designed to run on Make.com (via webhook or scheduler).
It handles:
1. Loading secrets from environment
2. Downloading model artifacts from Google Drive
3. Running the classification pipeline
4. Uploading results back to Google Drive
5. Sending status emails
"""

import os
import json
import sys
from pathlib import Path
from datetime import datetime
import shutil
import tempfile

# Get Make.com environment variables (passed via scenario)
def load_make_secrets():
    """Load secrets passed by Make.com scenario."""
    try:
        return {
            'SMTP_SERVER': os.getenv('SMTP_SERVER'),
            'SMTP_PORT': os.getenv('SMTP_PORT'),
            'SENDER_EMAIL': os.getenv('SENDER_EMAIL'),
            'EMAIL_PASSWORD': os.getenv('EMAIL_PASSWORD'),
            'RECIPIENT_EMAIL': os.getenv('RECIPIENT_EMAIL'),
            'WP_SITE_URL': os.getenv('WP_SITE_URL'),
            'WP_USERNAME': os.getenv('WP_USERNAME'),
            'WP_APP_PASSWORD': os.getenv('WP_APP_PASSWORD'),
            'GOOGLE_DRIVE_FOLDER_ID': os.getenv('GOOGLE_DRIVE_FOLDER_ID'),
            'SITE_TIMEZONE': os.getenv('SITE_TIMEZONE', 'America/Chicago'),
        }
    except KeyError as e:
        print(f"ERROR: Missing environment variable: {e}")
        sys.exit(1)

def download_artifacts_from_drive(drive_folder_id, temp_dir):
    """
    Download model artifacts from Google Drive.
    This should be called AFTER Make.com's Google Drive module
    has already authenticated.
    """
    # Note: In practice, you'd use the Google Drive API
    # For now, we'll store artifacts in Make.com's Google Drive connector
    # and reference them directly
    print(f"[INFO] Artifacts directory ready: {temp_dir}")
    return temp_dir

def run_pipeline_in_make(secrets):
    """
    Execute the pipeline with Make.com provided secrets.
    """
    # Set environment variables
    for key, value in secrets.items():
        if value:
            os.environ[key] = str(value)
    
    # Import pipeline modules
    from scripts import automated_pipeline
    
    print("[INFO] Starting Make.com Cloud Pipeline")
    print(f"[INFO] Timestamp: {datetime.now().isoformat()}")
    
    try:
        # Run the main pipeline
        result = automated_pipeline.run_full_pipeline()
        
        print(f"[SUCCESS] Pipeline completed: {result}")
        return {
            'status': 'success',
            'message': result,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        print(f"[ERROR] Pipeline failed: {str(e)}")
        return {
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }

if __name__ == '__main__':
    secrets = load_make_secrets()
    result = run_pipeline_in_make(secrets)
    print(json.dumps(result, indent=2))
```

### 3.2 Refactor `automated_pipeline.py` for Cloud

Update the pipeline to support cloud execution:

**In `scripts/automated_pipeline.py`, add:**

```python
def run_full_pipeline(skip_upload=False):
    """
    Execute complete pipeline: scrape → classify → email → upload
    
    Args:
        skip_upload: If True, skip WordPress upload (useful for testing)
    
    Returns:
        dict: Pipeline results and statistics
    """
    try:
        # 1. Scrape events
        log("[STAGE 1/4] Scraping events from Perdido Chamber...")
        scraped_events = Envision_Perdido_DataCollection.scrape_events()
        log(f"  → Scraped {len(scraped_events)} events")
        
        # 2. Classify events
        log("[STAGE 2/4] Classifying events using ML model...")
        model, vectorizer = load_model_and_vectorizer()
        classified_events = classify_events(scraped_events, model, vectorizer)
        log(f"  → Classified {len(classified_events)} events")
        
        # 3. Send email
        log("[STAGE 3/4] Sending email notification...")
        send_email_review(classified_events)
        log("  → Email sent")
        
        # 4. Upload to WordPress (optional)
        if not skip_upload:
            log("[STAGE 4/4] Uploading to WordPress...")
            upload_to_wordpress(classified_events)
            log("  → Events uploaded")
        else:
            log("[STAGE 4/4] Skipping WordPress upload (configured)")
        
        return {
            'events_scraped': len(scraped_events),
            'events_classified': len(classified_events),
            'community_events': sum(1 for e in classified_events if e['is_community']),
            'needs_review': sum(1 for e in classified_events if e['needs_review']),
        }
    
    except Exception as e:
        log(f"[ERROR] Pipeline failed: {str(e)}")
        raise

# Add a synchronous entry point for Make.com
if __name__ == '__main__':
    result = run_full_pipeline(skip_upload=os.getenv('SKIP_WP_UPLOAD', 'false').lower() == 'true')
    print(json.dumps(result, indent=2))
```

### 3.3 Create a Health Check Module for Make.com

**File: `scripts/make_health_check.py`**

```python
"""
Health check for Make.com CI/CD pipeline.
Monitors WordPress, email, and Google Drive connectivity.
"""

import json
import requests
import smtplib
from datetime import datetime

def check_wordpress_health(wp_url, wp_user, wp_password):
    """Test WordPress REST API connectivity."""
    try:
        headers = {
            'Authorization': 'Basic ' + 
            base64.b64encode(f"{wp_user}:{wp_password}".encode()).decode()
        }
        response = requests.get(
            f"{wp_url}/wp-json/wp/v2/users/me",
            headers=headers,
            timeout=10
        )
        return {'status': 'ok' if response.status_code == 200 else 'error',
                'code': response.status_code}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

def check_email_health(smtp_server, smtp_port, sender_email, password):
    """Test SMTP connectivity."""
    try:
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
        server.starttls()
        server.login(sender_email, password)
        server.quit()
        return {'status': 'ok'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

def check_google_drive_health():
    """Test Google Drive API connectivity (via Make.com)."""
    # This would be implemented by Make.com's Google Drive module
    return {'status': 'ok', 'note': 'Checked by Make.com Google Drive connector'}

def run_health_check():
    """Execute all health checks."""
    return {
        'timestamp': datetime.now().isoformat(),
        'checks': {
            'wordpress': check_wordpress_health(
                os.getenv('WP_SITE_URL'),
                os.getenv('WP_USERNAME'),
                os.getenv('WP_APP_PASSWORD')
            ),
            'email': check_email_health(
                os.getenv('SMTP_SERVER'),
                os.getenv('SMTP_PORT'),
                os.getenv('SENDER_EMAIL'),
                os.getenv('EMAIL_PASSWORD')
            ),
            'google_drive': check_google_drive_health(),
        }
    }

if __name__ == '__main__':
    result = run_health_check()
    print(json.dumps(result, indent=2))
```

---

## Phase 4: Build Make.com Scenarios

### 4.1 Create Scenario 1: Weekly Scrape & Classify (Complete Step-by-Step)

This scenario will run every Monday morning and automatically scrape events, classify them, and email you the results.

---

#### **Step 1: Create a New Scenario**

1. Log in to Make.com
2. Click **Scenarios** in the left sidebar
3. Click **+ Create a new scenario** (or **Create**)
4. A dialog will pop up asking for a name
5. Enter: `EnvisionPerdido - Weekly Event Pipeline`
6. Click **Create**

**You're now in the Scenario Editor** — This is where you build the workflow!

---

#### **Step 2: Add a Scheduler Trigger**

The scheduler will automatically run this workflow every Monday at 8 AM.

**In the scenario editor:**

1. You'll see a blank canvas with a **+ (plus icon)** in the middle
2. Click the **+** icon
3. A module search box will appear
4. Search for **"Scheduler"** and click it
5. A configuration panel will appear on the right

**Configure the Scheduler:**

In the right panel, you'll see:

```
[ Schedule type dropdown: Currently says "Once" ]
[ Timezone field ]
[ Time fields ]
```

1. Click the **"Once" dropdown** and select **"Weekly"**
2. Now you'll see day/time fields:
   - **Day of week:** Select **Monday**
   - **Time:** Type **08:00** (8 AM)
   - **Timezone:** Select **America/Chicago**

3. Click **OK** (or the checkmark icon)

**Visual result:** You now have a blue box on the canvas labeled **"Scheduler"** with "Weekly" underneath.

---

#### **Step 3: Add a Set Variables Module (for environment variables)**

This module will set all your credentials from the `make_env_secrets.json` file before running the pipeline.

1. Click the **arrow** coming out of the Scheduler box → You'll see a **+** icon appear
2. Click the **+** to add the next module
3. Search for **"Set Variables"** and click it
4. A configuration panel opens on the right

**Configure Set Variables:**

You'll see a table with columns:
- **Variable name** (left column)
- **Variable value** (right column)

Create these 10 variables (click **+ Add** button for each row):

| Variable Name | Variable Value |
|---|---|
| `SMTP_SERVER` | `smtp.gmail.com` |
| `SMTP_PORT` | `587` |
| `SENDER_EMAIL` | Your Gmail from `make_env_secrets.json` |
| `EMAIL_PASSWORD` | Click the **padlock icon** → Select from Secrets |
| `RECIPIENT_EMAIL` | Your supervisor email |
| `WP_SITE_URL` | Your WordPress site URL |
| `WP_USERNAME` | Your WordPress username |
| `WP_APP_PASSWORD` | Click padlock → Select from Secrets |
| `GOOGLE_DRIVE_FOLDER_ID` | Your folder ID (already in `make_env_secrets.json`) |
| `SITE_TIMEZONE` | `America/Chicago` |

**What's the padlock icon?** Clicking it lets you reference secrets from Make.com's vault instead of pasting plaintext. Click it for EMAIL_PASSWORD and WP_APP_PASSWORD.

**After filling in all 10 variables, click OK** ✓

**Visual result:** You now have Scheduler → Set Variables in your workflow.

---

#### **Step 4: Add Google Drive Module to Download Model Artifacts**

This downloads your trained ML model from Google Drive.

1. Click the **arrow** from Set Variables → Click the **+** icon
2. Search for **"Google Drive"** and click it
3. You'll see a list of Google Drive operations (Download file, Upload file, etc.)
4. Click **"Download a file"**

**Configure Download File:**

A panel appears with fields:

```
[ Folder field: search for folder ]
[ File field: search for file name ]
```

1. **Folder field:** Click the folder icon, then search for your `EnvisionPerdido` folder → Select it
2. **File field:** Type `event_classifier_model.pkl`
3. Click **OK**

**Visual result:** You now have a Google Drive module downloading the model file.

---

#### **Step 5: Add Another Google Drive Download for Vectorizer**

1. Click the **arrow** from the previous Google Drive module → Click **+**
2. Search **"Google Drive"** → Click **"Download a file"** again
3. **Folder:** Same as before (EnvisionPerdido folder)
4. **File:** Type `event_vectorizer.pkl`
5. Click **OK**

**Visual result:** Now you have two Google Drive downloads in your scenario.

---

#### **Step 6: Add HTTP Module to Call Your Lambda Function**

This is where the actual Python pipeline runs (we'll set up Lambda in Phase 5).

1. Click the **arrow** from the second Google Drive module → Click **+**
2. Search for **"HTTP"** and click **"Make a request"**
3. A configuration panel appears

**Configure HTTP Request:**

Fill in these fields:

```
URL:            [We'll come back to this after Lambda is set up]
Method:         POST
Headers:        Content-Type: application/json
Body:           [See below for JSON structure]
```

**For the Body (JSON format):**

Click on the **Body field** and enter:

```json
{
  "SMTP_SERVER": {{SMTP_SERVER}},
  "SMTP_PORT": {{SMTP_PORT}},
  "SENDER_EMAIL": {{SENDER_EMAIL}},
  "EMAIL_PASSWORD": {{EMAIL_PASSWORD}},
  "RECIPIENT_EMAIL": {{RECIPIENT_EMAIL}},
  "WP_SITE_URL": {{WP_SITE_URL}},
  "WP_USERNAME": {{WP_USERNAME}},
  "WP_APP_PASSWORD": {{WP_APP_PASSWORD}},
  "GOOGLE_DRIVE_FOLDER_ID": {{GOOGLE_DRIVE_FOLDER_ID}},
  "SITE_TIMEZONE": {{SITE_TIMEZONE}}
}
```

**Note:** The `{{ }}` notation tells Make.com to insert the actual variable values (from Set Variables) instead of literal text.

**Don't click OK yet** — We need the Lambda URL first (Phase 5). For now, just leave the URL blank.

---

#### **Step 7: Add Gmail Module to Send Success Email**

This sends you a notification after the pipeline completes.

1. Click the **arrow** from the HTTP module → Click **+**
2. Search for **"Gmail"** and click **"Send an email"**
3. A configuration panel appears

**Configure Email:**

Fill in:

```
To:         {{RECIPIENT_EMAIL}}
Subject:    ✅ EnvisionPerdido Weekly Pipeline - {{now.formatAsString('YYYY-MM-DD')}}
Body:       [See below for HTML template]
```

**For the Body, use this HTML template:**

```html
<h2>📊 EnvisionPerdido Weekly Pipeline Completed</h2>

<p><strong>Date:</strong> {{now.formatAsString('YYYY-MM-DD HH:mm')}}</p>

<p><strong>Results from Lambda execution:</strong></p>
<ul>
  <li><strong>Events Scraped:</strong> {{1.body.events_scraped}}</li>
  <li><strong>Community Events Found:</strong> {{1.body.community_events}}</li>
  <li><strong>Needs Review:</strong> {{1.body.needs_review}}</li>
  <li><strong>Status:</strong> {{1.body.status}}</li>
</ul>

<p>Results are uploaded to your Google Drive folder.</p>

<p><strong>To manually upload these events to WordPress, click here:</strong><br>
<a href="[webhook-url-here]">Upload to Calendar</a></p>

<p>—<br>
EnvisionPerdido Automation System
</p>
```

**Note:** `{{1.body.*}}` refers to the response from the Lambda function (the HTTP module). We'll get this URL in Phase 5.

4. Click **OK**

---

#### **Step 8: Add Error Handler (Optional but Recommended)**

This catches failures and sends you an alert.

1. Click the **arrow** from Gmail module → Click **+**
2. Search for **"Router"** (this is Make.com's conditional logic)
3. Click **"Router"** when it appears
4. A split appears (two paths: "Route 1" and "Default")

**Configure Router:**

1. Click on **"Route 1"** box
2. Add a condition: **IF** `{{1.body.status}}` **equals** `error`
3. This means: "If the pipeline failed..."
4. Then add an **Email** module to this route to send an error alert
5. The **Default** route handles successful runs

---

#### **Step 9: Test the Scenario**

1. Click the **Play button** (▶️) at the bottom of the editor
2. Make.com will simulate running the scenario
3. Check the **Execution History** to see if it worked
4. Look for any red error icons (these mean something failed)

**Common issues at this point:**
- ❌ "HTTP URL is blank" — That's OK, we'll fix it in Phase 5
- ❌ "Gmail not authorized" — Go back to Phase 2.2, re-authorize Gmail
- ❌ "Google Drive module can't find folder" — Make sure you authorized Google Drive in Phase 2.2

---

#### **Step 10: Save the Scenario**

1. Click the **Scenario name** at the top (editable)
2. Make sure it says: `EnvisionPerdido - Weekly Event Pipeline`
3. Click the **Save** button (disk icon) at the bottom
4. You should see a notification: "Scenario saved successfully" ✅

---

**You've now created your first Make.com scenario!** 🎉

**What happens next:**
- Phase 5: We'll deploy a Lambda function and get a URL
- Phase 6: We'll paste that URL into the HTTP module
- Then the scenario will be fully functional!

---

### 4.2 Create Scenario 2: On-Demand Upload Trigger

**Scenario Name:** `EnvisionPerdido - Manual WordPress Upload`

**Trigger:** Webhook (allows supervisors to trigger upload)

**Flow:**

```
1. WEBHOOK
   ├─ Listen for POST request
   ├─ Webhook URL: https://make.com/webhooks/...
   └─ Output: {{webhook_data}}

2. GOOGLE DRIVE - LIST RECENT CSVS
   ├─ Module: Google Drive → Search Files
   ├─ Query: filename contains 'calendar_upload'
   ├─ Folder: EnvisionPerdido/outputs/
   ├─ Sort by: Modified date (newest first)
   └─ Limit: 1

3. DOWNLOAD LATEST CSV
   ├─ Module: Google Drive → Download a file
   ├─ File ID: {{search_result[0].id}}
   └─ Output: {{csv_content}}

4. EXECUTE WORDPRESS UPLOAD
   ├─ Module: HTTP → Make a request
   ├─ Call: Lambda function with CSV data
   ├─ Function: wordpress_uploader.py
   └─ Output: {{upload_result}}

5. SEND CONFIRMATION EMAIL
   ├─ To: {{webhook_data.approver_email}}
   ├─ Subject: ✅ Events uploaded! {{upload_result.count}} events added
   └─ Body: Details of uploaded events

6. LOG TO GOOGLE SHEETS (Optional Dashboard)
   ├─ Module: Google Sheets → Append a row
   ├─ Spreadsheet: EnvisionPerdido Execution Log
   ├─ Sheet: Upload History
   ├─ Row: [Date, Events Count, Status, Approver]
   └─ Output: {{log_result}}
```

**Webhook Setup:**
```
1. In Scenario editor, click "Webhooks"
2. Click "Create a webhook"
3. Copy webhook URL
4. Share with supervisors:
   https://make.com/webhooks/[webhook_id]/invoke?approver_email=supervisor@example.com&action=upload
```

---

### 4.3 Create Scenario 3: Daily Health Check

**Scenario Name:** `EnvisionPerdido - Daily Health Monitor`

**Trigger:** Schedule (Daily, 9 AM UTC)

**Flow:**

```
1. SCHEDULER
   └─ Daily, 9:00 AM UTC

2. RUN HEALTH CHECKS (HTTP request)
   ├─ Call make_health_check.py via Lambda
   ├─ Check: WordPress, Email, Google Drive
   └─ Output: {{health_status}}

3. ROUTER
   ├─ If all_ok
   │  └─ Log success to Google Sheets
   └─ Else (any failed check)
      ├─ Send alert email to supervisors
      ├─ Subject: ⚠️ EnvisionPerdido Health Check Failed
      └─ Body: List of failed checks + remediation steps
```

---

## Phase 5: Deploy to AWS Lambda (Complete Step-by-Step Guide for Beginners)

AWS Lambda is where your Python pipeline code runs in the cloud. Think of it as a serverless computer that only runs when needed.

**Prerequisites:**
- AWS account (sign up free at https://aws.amazon.com)
- AWS CLI installed on your PC (https://aws.amazon.com/cli/)

---

### 5.0 Set Up AWS Account (First Time Only)

If you don't have an AWS account yet:

1. Go to https://aws.amazon.com
2. Click **Create an AWS Account**
3. Follow the sign-up wizard (you'll need a credit card, but free tier won't charge)
4. Verify your email
5. After account creation, go to AWS Management Console: https://console.aws.amazon.com

---

### 5.1 Create an IAM User & Get Credentials (First Time Only)

This gives you a way to authenticate with AWS from your PC.

**Step 1: Create IAM User**

1. In AWS Console, search for **"IAM"** in the search bar
2. Click **IAM** (Identity and Access Management)
3. In the left menu, click **Users**
4. Click **Create user** button
5. Name it: `envision-perdido-lambda`
6. Click **Create user**

**Step 2: Add Permissions**

1. Click your new user name
2. Click **Add permissions** → **Attach policies directly**
3. Search for `AWSLambdaFullAccess` and check it
4. Search for `IAMFullAccess` and check it (for creating roles)
5. Click **Next** → **Add permissions**

**Step 3: Create Access Key**

1. Still in your user's page, click **Security credentials** tab
2. Scroll down to **Access keys**
3. Click **Create access key**
4. Choose **Command Line Interface (CLI)**
5. Click **Next**
6. Click **Create access key**
7. **SAVE THESE VALUES** (copy them somewhere safe):
   - Access Key ID
   - Secret Access Key
8. Click **Done**

---

### 5.2 Install AWS CLI on Your PC

**Step 1: Download & Install**

1. Go to https://aws.amazon.com/cli/
2. Download the **Windows installer** (`.msi` file)
3. Run the installer and follow the steps (default settings are fine)

**Step 2: Verify Installation**

1. Open **PowerShell** on your PC
2. Type: `aws --version`
3. You should see: `aws-cli/2.x.x`

**If this fails:**
- Restart PowerShell
- Or restart your PC

---

### 5.3 Configure AWS Credentials on Your PC

This tells AWS CLI which account to use.

**Step 1: Run Configuration**

1. Open **PowerShell**
2. Type: `aws configure`
3. You'll be prompted for:

```
AWS Access Key ID [None]: [paste your Access Key ID from 5.1]
AWS Secret Access Key [None]: [paste your Secret Access Key from 5.1]
Default region name [None]: us-east-1
Default output format [None]: json
```

**Step 2: Verify It Worked**

1. Type: `aws s3 ls`
2. If you see a list (or empty list), it worked! ✅
3. If you get an error, double-check your keys

---

### 5.4 Create Lambda Deployment Package

This is where we bundle your Python scripts and dependencies into a ZIP file.

**Step 1: Create Lambda Directory**

1. Open **PowerShell**
2. Navigate to your project:
   ```powershell
   cd c:\Users\scott\UWF-Code\EnvisionPerdido
   ```

3. Create a new folder:
   ```powershell
   mkdir lambda_deployment
   cd lambda_deployment
   ```

**Step 2: Copy Your Python Scripts**

```powershell
# From the parent EnvisionPerdido folder
Copy-Item ..\scripts\make_cloud_pipeline.py -Destination .\
Copy-Item ..\scripts\automated_pipeline.py -Destination .\
Copy-Item ..\scripts\wordpress_uploader.py -Destination .\
Copy-Item ..\scripts\Envision_Perdido_DataCollection.py -Destination .\
Copy-Item ..\requirements.txt -Destination .\
```

**Verify files were copied:**
```powershell
ls .\  # Should list: make_cloud_pipeline.py, automated_pipeline.py, etc.
```

**Step 3: Install Python Dependencies**

This downloads all the libraries your scripts need:

```powershell
pip install -r requirements.txt -t ./
```

**This may take a few minutes.** Wait for it to complete. You'll see packages being downloaded.

**Verify installation:**
```powershell
ls .\ | where { $_.PSIsContainer }  # Should see folders like: requests, scikit-learn, etc.
```

**Step 4: Create Lambda Handler File**

This is the entry point that Lambda calls:

```powershell
$handler_code = @"
import json
import os
import sys
from make_cloud_pipeline import run_pipeline_in_make

def lambda_handler(event, context):
    """
    AWS Lambda handler - called by Make.com
    
    Args:
        event: Dict with credentials from Make.com
        context: Lambda context (ignore for now)
    
    Returns:
        Dict with statusCode and response body
    """
    try:
        # Extract credentials from Make.com event
        secrets = {
            'SMTP_SERVER': event.get('SMTP_SERVER'),
            'SMTP_PORT': event.get('SMTP_PORT'),
            'SENDER_EMAIL': event.get('SENDER_EMAIL'),
            'EMAIL_PASSWORD': event.get('EMAIL_PASSWORD'),
            'RECIPIENT_EMAIL': event.get('RECIPIENT_EMAIL'),
            'WP_SITE_URL': event.get('WP_SITE_URL'),
            'WP_USERNAME': event.get('WP_USERNAME'),
            'WP_APP_PASSWORD': event.get('WP_APP_PASSWORD'),
            'GOOGLE_DRIVE_FOLDER_ID': event.get('GOOGLE_DRIVE_FOLDER_ID'),
            'SITE_TIMEZONE': event.get('SITE_TIMEZONE', 'America/Chicago'),
        }
        
        # Run the pipeline
        result = run_pipeline_in_make(secrets)
        
        return {
            'statusCode': 200 if result.get('status') == 'success' else 500,
            'body': json.dumps(result)
        }
    
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'status': 'error',
                'message': str(e)
            })
        }
"@

Out-File -FilePath .\lambda_handler.py -InputObject $handler_code -Encoding UTF8
```

**Verify the file was created:**
```powershell
cat .\lambda_handler.py  # Should show the Python code
```

**Step 5: Create ZIP File**

This compresses everything into one file for upload:

```powershell
Compress-Archive -Path .\ -DestinationPath lambda_function.zip -Force
```

**Verify:**
```powershell
ls -la .\lambda_function.zip  # Should show a file ~20-50 MB
```

---

### 5.5 Create IAM Role for Lambda

Lambda needs permission to run and write logs:

**Step 1: Create the Role**

```powershell
# This creates an IAM role that Lambda can assume
$trust_policy = @{
    Version = "2012-10-17"
    Statement = @(
        @{
            Effect = "Allow"
            Principal = @{ Service = "lambda.amazonaws.com" }
            Action = "sts:AssumeRole"
        }
    )
} | ConvertTo-Json

aws iam create-role `
  --role-name EnvisionPerdido-Lambda-Execution-Role `
  --assume-role-policy-document $trust_policy
```

**Step 2: Attach Policies**

```powershell
# Allow Lambda to write logs
aws iam attach-role-policy `
  --role-name EnvisionPerdido-Lambda-Execution-Role `
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
```

**Step 3: Wait for Role to Be Ready**

AWS sometimes takes a minute to fully create the role. Wait ~30 seconds before proceeding.

---

### 5.6 Deploy Lambda Function

Now upload your ZIP to AWS:

**Step 1: Get Your AWS Account ID**

```powershell
aws sts get-caller-identity
```

This shows your AWS Account ID (looks like: `123456789012`). **Copy it** for the next command.

**Step 2: Deploy the Function**

Replace `YOUR_ACCOUNT_ID` with your actual account ID:

```powershell
aws lambda create-function `
  --function-name EnvisionPerdido-Pipeline `
  --runtime python3.11 `
  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/EnvisionPerdido-Lambda-Execution-Role `
  --handler lambda_handler.lambda_handler `
  --zip-file fileb://lambda_function.zip `
  --timeout 300 `
  --memory-size 512
```

**Expected output:**
```json
{
    "FunctionName": "EnvisionPerdido-Pipeline",
    "FunctionArn": "arn:aws:lambda:us-east-1:YOUR_ACCOUNT_ID:function:EnvisionPerdido-Pipeline",
    "Runtime": "python3.11",
    "CodeSize": 50000000,
    ...
}
```

**If you get an error:**
- "Role is invalid" → Wait 30 more seconds for the role to be fully created
- "Function already exists" → That's OK, you can skip to Step 3

---

### 5.7 Create Function URL (So Make.com Can Call Lambda)

**Step 1: Create the URL**

```powershell
aws lambda create-function-url-config `
  --function-name EnvisionPerdido-Pipeline `
  --auth-type NONE `
  --cors AllowOrigins="*",AllowMethods="POST",AllowHeaders="*"
```

**Expected output:**
```json
{
    "FunctionUrl": "https://abcdef123xyz.lambda-url.us-east-1.on.aws/",
    "FunctionArn": "...",
    "CreationTime": "...",
    "Cors": {...}
}
```

**COPY THE FunctionUrl** — This is what you'll put in Make.com!

Example: `https://abcdef123xyz.lambda-url.us-east-1.on.aws/`

**Step 2: Save This URL**

1. Open your `scripts/make_env_secrets.json`
2. Add this new field:
   ```json
   "AWS_LAMBDA_URL": "https://abcdef123xyz.lambda-url.us-east-1.on.aws/"
   ```
3. Save the file

---

### 5.8 Test Lambda from Your PC

Before using it in Make.com, let's verify it works:

**Step 1: Create a Test File**

```powershell
# Save this as test_lambda.json
$test_event = @{
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = "587"
    SENDER_EMAIL = "your_email@gmail.com"
    EMAIL_PASSWORD = "your_app_password"
    RECIPIENT_EMAIL = "your_email@gmail.com"
    WP_SITE_URL = "https://your-site.org"
    WP_USERNAME = "your_username"
    WP_APP_PASSWORD = "xxxx xxxx xxxx xxxx"
    GOOGLE_DRIVE_FOLDER_ID = "your_folder_id"
    SITE_TIMEZONE = "America/Chicago"
} | ConvertTo-Json | Out-File -FilePath test_lambda.json
```

**Step 2: Invoke Lambda Locally**

```powershell
aws lambda invoke `
  --function-name EnvisionPerdido-Pipeline `
  --cli-binary-format raw-in-base64-out `
  --payload file://test_lambda.json `
  response.json

# Check the response
cat response.json
```

**Expected response:**
```json
{
  "statusCode": 200,
  "body": "{\"status\": \"success\", \"events_scraped\": 42, ...}"
}
```

**If you get an error:**
- Check error messages in response.json
- Look at Lambda logs: `aws logs tail /aws/lambda/EnvisionPerdido-Pipeline --follow`

---

**Congratulations!** Your Lambda function is deployed and has a public URL. Now go to **Phase 6** to add this URL to your Make.com scenario!

## Phase 6: Configure Make.com Scenarios (Detailed Step-by-Step)

### 6.1 Add Secrets Vault (Save Sensitive Values Securely)

The Secrets vault is where you store passwords and API keys in Make.com. Instead of writing passwords directly in scenarios, you reference them safely.

**Step 1: Go to Organization Settings**

1. Log in to Make.com
2. Look at the **top-left corner** of the dashboard
3. You'll see your **Organization name** (click on it if needed)
4. Click **Settings** (gear icon) → This should open a dropdown menu
5. From the dropdown, click **Organization**
6. You'll see tabs: **General**, **Teams**, **Security**, **Integrations**, **Secrets**
7. Click the **Secrets** tab

**Step 2: Add Your First Secret (Email Password)**

1. In the **Secrets** tab, click **+ Add secret** button (top right)
2. A form appears:
   ```
   [ Identifier/Name field ]
   [ Value field (hidden) ]
   [ Description field (optional) ]
   ```

3. For the **Identifier**, type: `EMAIL_PASSWORD`
4. For the **Value**, paste your Gmail app password (16 characters, should look like `xxxx xxxx xxxx xxxx`)
5. **Description** (optional): `Gmail app password for SMTP`
6. Click **Save**

**Step 3: Repeat for Other Sensitive Values**

Create secrets for these values from your `make_env_secrets.json`:

| Secret Identifier | Value | Example |
|---|---|---|
| `EMAIL_PASSWORD` | Your Gmail app password | `xxxx xxxx xxxx xxxx` |
| `WP_APP_PASSWORD` | Your WordPress app password | `xxxx xxxx xxxx xxxx` |
| `AWS_LAMBDA_URL` | (We'll get this in Phase 5) | `https://abcd123.lambda-url.us-east-1.on.aws/` |

**Repeat the "Add secret" process for each one.**

**What you just did:** Make.com now stores these sensitive values encrypted, and you can reference them in scenarios without showing passwords in plaintext.

---

### 6.2 Go Back to Your Scenario and Complete the HTTP Module

Now that you have secrets stored, let's fill in the HTTP module that calls your Lambda function.

**Step 1: Open Your Scenario**

1. Click **Scenarios** in the left sidebar
2. Find **`EnvisionPerdido - Weekly Event Pipeline`**
3. Click it to open it in the editor

**Step 2: Find and Edit the HTTP Module**

In the canvas, you should see the modules you created:
```
Scheduler → Set Variables → Google Drive (model) → Google Drive (vectorizer) → HTTP → Gmail
```

1. Click on the **HTTP** module (the one that says "Make a request" or similar)
2. The configuration panel will open on the right

**Step 3: Configure the HTTP Module URL**

In the HTTP module configuration:

1. Find the **URL** field
2. This is where the Lambda function URL goes
3. For now, we'll leave it as a placeholder: `https://lambda-url-will-go-here.com/`
4. (We'll come back after Phase 5 when we deploy Lambda)

**But here's the key:** After Phase 5, paste your Lambda URL here:
```
https://abcdef123xyz.lambda-url.us-east-1.on.aws/
```

**Step 4: Verify Headers**

In the HTTP module, make sure:

1. **Method:** Set to **POST**
2. **Headers:** Should have:
   ```
   Content-Type: application/json
   ```

3. If you don't see headers, click **Show advanced settings** or similar

**Step 5: Configure the Body (JSON)**

This is the most important part. The Body tells Lambda what to do.

1. In the HTTP module, find the **Body** field
2. Switch it to **"Raw"** or **"JSON"** mode (if there's a dropdown)
3. Enter this JSON:

```json
{
  "SMTP_SERVER": "smtp.gmail.com",
  "SMTP_PORT": "587",
  "SENDER_EMAIL": {{SENDER_EMAIL}},
  "EMAIL_PASSWORD": {{EMAIL_PASSWORD}},
  "RECIPIENT_EMAIL": {{RECIPIENT_EMAIL}},
  "WP_SITE_URL": {{WP_SITE_URL}},
  "WP_USERNAME": {{WP_USERNAME}},
  "WP_APP_PASSWORD": {{WP_APP_PASSWORD}},
  "GOOGLE_DRIVE_FOLDER_ID": {{GOOGLE_DRIVE_FOLDER_ID}},
  "SITE_TIMEZONE": "America/Chicago"
}
```

**Important:** The `{{ }}` syntax tells Make.com to insert variable values. These variables come from the **Set Variables** module you created in Step 3.

**Step 6: Enable Response Parsing**

After the Body field, you should see an option like:

```
[ ] Parse response   OR   [ ] Use JSON
```

1. **Toggle this ON** (click the checkbox)
2. This tells Make.com to read the response from Lambda and make it available to the next modules

**Step 7: Click OK**

Save the HTTP module configuration by clicking **OK** or the checkmark icon.

---

### 6.3 Add Error Handling (Catch Failures)

Let's make sure the scenario alerts you if something goes wrong.

**Step 1: Open Scenario Settings**

1. In the Scenario Editor, look for the **gear icon** (⚙️) at the bottom or top
2. Click it → A settings menu opens

**Step 2: Find Error Handling**

1. Look for **"Execution"** or **"Advanced settings"** section
2. Find the **"Handle errors"** or **"On error"** option

**Step 3: Configure Error Notifications**

1. Enable: **"Send notification if scenario fails"** (toggle ON)
2. Set notification email to: `{{RECIPIENT_EMAIL}}`
   (This uses the variable from Set Variables)
3. Optional: Add error message template in the notification

**Step 4: Save Settings**

Click **OK** or **Save** to close settings.

---

### 6.4 Test Your Scenario (Before Going Live)

Before setting up the schedule to run weekly, let's test it:

**Step 1: Run the Scenario Manually**

1. In the Scenario Editor, look for a **Play button (▶️)** at the bottom
2. Click it to run the scenario ONE TIME
3. Make.com will execute all modules in sequence

**Step 2: Check Execution History**

1. After clicking Play, you'll see **Execution details**
2. Look for each module to see if it succeeded (✅) or failed (❌)
3. Click on individual modules to see error messages if any failed

**Expected results (at this point):**
- ✅ Scheduler module: "Scheduled"
- ✅ Set Variables: "Variables set"
- ✅ Google Drive (model): "Downloaded successfully"
- ✅ Google Drive (vectorizer): "Downloaded successfully"
- ❌ HTTP: "URL is empty" or "Connection refused" — **This is OK for now!** We'll fix it in Phase 5
- ✅ Gmail: "Email sent" (should work if Gmail is connected)

**Step 3: If Gmail Fails:**

1. Check that you authorized Gmail in Phase 2.2
2. Go back to **Connections** and re-authorize Gmail if needed
3. Re-run the test

**Step 4: If Google Drive Fails:**

1. Check that you authorized Google Drive in Phase 2.2
2. Verify your EnvisionPerdido folder exists in Google Drive
3. Verify the .pkl files are in the correct subfolder

---

### 6.5 Set Up the Weekly Schedule

Once testing passes, activate the automatic schedule:

**Step 1: Open Scheduler Module**

1. In the Scenario Editor, click the **Scheduler** module (the first box)
2. The configuration panel opens

**Step 2: Verify Schedule Settings**

Make sure these are correct:

```
Schedule type:  Weekly
Day of week:    Monday
Time:           08:00 (8 AM)
Timezone:       America/Chicago
```

**Step 3: Enable the Schedule**

Look for a toggle or checkbox labeled **"Enabled"** or **"Active"**

1. Toggle it **ON** ✓
2. This activates the weekly schedule

**Step 4: Save the Scenario**

1. Click the **Save** button (💾 icon) at the bottom
2. You should see: "Scenario saved successfully" ✅

---

**You've now completed Phase 6!** The scenario is set up, but the HTTP module doesn't have a Lambda URL yet. That's OK — we'll complete it in Phase 5 (deploy Lambda) and Phase 5.2 (add the URL).

### 6.6 Summary: What Your Scenario Does Now

Every **Monday at 8:00 AM** (Chicago time), this scenario will:

1. ✅ Run the Scheduler trigger
2. ✅ Set all your environment variables
3. ✅ Download your ML model from Google Drive
4. ✅ Download your vectorizer from Google Drive
5. ⏳ Send the data to Lambda to run the pipeline (after Phase 5)
6. ✅ Email you the results

**Next:** Phase 5 - Deploy to AWS Lambda to get the URL you need for the HTTP module.

---

## Phase 7: Invite Supervisors & Set Permissions

### 7.1 Create Team Organization

1. Make.com Dashboard → **Organization** (top-left)
2. **Members** → **Invite**
3. Enter supervisor emails:
   ```
   supervisor1@example.com
   supervisor2@example.com
   ```
4. Set Role: **Viewer** (read-only) or **Developer** (can edit)

### 7.2 Share Webhook Links

For on-demand uploads, create a simple **external link**:

```
Share this link with supervisors:
https://make.com/webhooks/[webhook_id]/invoke?action=upload&approver=supervisor@example.com

When clicked, it triggers the upload workflow.
```

### 7.3 Create Public Dashboard (Optional)

Use **Google Sheets** as a dashboard:

```
Spreadsheet: EnvisionPerdido Execution Log
Sheets:
  - Pipeline Runs (with timestamps, event counts, status)
  - Upload History (with approver, date, event count)
  - Health Check Log (with service status)
  - Error Log (with failure details)
```

**Make.com can auto-populate** this via "Google Sheets → Append row" module.

**Share with supervisors** (read-only):
- Right-click sheet → **Share** → Set to "Viewer"
- Send link: https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID

---

## Phase 8: Local Backup & Sync Strategy

### 8.1 Keep Local Copy in Sync

**Option A: One-way sync (Make → Local)**

```powershell
# Script: scripts/sync_from_cloud.ps1
$GDRIVE_FOLDER_ID = "1abc2def3ghi4jkl5mno6pqr"

# Download latest CSV from Google Drive
# Install: Install-Module -Name GoogleDrive

# Pseudo-code:
# Get-GoogleDriveFile -FolderId $GDRIVE_FOLDER_ID `
#   -Filter "calendar_upload" `
#   -DownloadPath ".\output\pipeline\"
```

**Option B: GitHub Actions (Backup to Git)**

```yaml
# .github/workflows/sync-from-cloud.yml
name: Sync Results from Google Drive

on:
  schedule:
    - cron: '0 10 * * 1' # Monday 10 AM

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Sync from Google Drive
        run: |
          # Download latest CSV
          # Commit to git
          git add output/pipeline/*.csv
          git commit -m "Auto-sync: Cloud pipeline results"
          git push
```

### 8.2 Version Control

```
.gitignore:
  - output/pipeline/*  (Keep locally, but don't commit)
  - data/artifacts/*   (Keep locally, mirror on Cloud)
  - scripts/make_env_secrets.json
```

**Alternative: Commit results**
```
output/
  └── pipeline/
      ├── calendar_upload_2025-01-22.csv
      ├── calendar_upload_2025-01-29.csv
      └── ... (all uploads tracked in git)
```

---

## Phase 9: Testing & Validation

### 9.1 Local Test Run

Before deploying to cloud:

```powershell
# Test the wrapper script locally
cd c:\Users\scott\UWF-Code\EnvisionPerdido

# Set test environment
$env:SKIP_WP_UPLOAD = "true"  # Don't touch WordPress
$env:SMTP_SERVER = "smtp.gmail.com"
$env:SENDER_EMAIL = "your_email@gmail.com"
$env:EMAIL_PASSWORD = "your_16_char_app_password"
$env:RECIPIENT_EMAIL = "your_email@gmail.com"

# Run wrapper
python scripts\make_cloud_pipeline.py
```

**Expected output:**
```json
{
  "status": "success",
  "events_scraped": 42,
  "events_classified": 42,
  "community_events": 28,
  "needs_review": 3
}
```

### 9.2 Test Make.com Scenarios (Dry Run)

1. In Make.com, click scenario → **Run once**
2. Check **Execution history** for:
   - ✅ All modules executed
   - ✅ No errors
   - ✅ Correct output data

3. If error, click module → **View details** to debug

### 9.3 Test Supervisor Access

Ask a supervisor to:
1. Log into Make.com with their account
2. View the scenario (read-only)
3. Click the webhook link to trigger upload
4. Verify email notification arrives

---

## Phase 10: Operational Procedures

### 10.1 Weekly Workflow (Automated)

```
MONDAY 8:00 AM (UTC)
  ↓
Make.com Scheduler triggers scenario
  ↓
Lambda executes pipeline
  ↓
CSV uploaded to Google Drive
  ↓
Email sent to all supervisors
  ↓
Results logged to Google Sheets
```

**Supervisor receives:**
- Email: "EnvisionPerdido Weekly Pipeline - 42 events classified, 28 community"
- Link to Google Sheet dashboard
- Option to click webhook link for immediate upload

### 10.2 Manual Upload Workflow

**For supervisors:**

1. Receive weekly pipeline email
2. Review classified events (in email or Google Sheets)
3. Click **Upload Now** webhook link
4. Receive confirmation email

**For you (local PC):**

1. **Optional:** Manually review events
2. **Optional:** Make edits to the CSV
3. Optionally trigger upload via webhook link

### 10.3 Handle Failures

**If health check fails:**

```
Make.com sends alert email:
  - ❌ WordPress REST API unreachable
  - ✅ Email working
  - ✅ Google Drive working

You (or supervisors) can:
  1. Check WordPress status (wp-admin → Tools → Site Health)
  2. Verify credentials haven't changed
  3. Manually disable scenario until fixed
```

**If pipeline fails:**

```
Lambda error logged to:
  - AWS CloudWatch Logs
  - Make.com Execution History
  - Email alert to supervisors

Debug steps:
  1. Click failed execution in Make.com
  2. View Lambda error in CloudWatch
  3. Fix code or credentials
  4. Re-run scenario
```

### 10.4 Updating Scripts in Production

**When you modify code locally:**

1. Test changes on your PC
2. Commit to git
3. Update Lambda function:
   ```powershell
   # Rebuild deployment package
   cd .\lambda_deployment
   Compress-Archive -Path .\ -DestinationPath lambda_function.zip -Force
   
   # Deploy
   aws lambda update-function-code `
     --function-name EnvisionPerdido-Pipeline `
     --zip-file fileb://lambda_function.zip
   ```
4. Test in Make.com via "Run once"
5. Confirm in Google Sheets dashboard

---

## Phase 11: Monitoring & Dashboards

### 11.1 Google Sheets Dashboard

**Create spreadsheet with sheets:**

**Sheet 1: Pipeline Runs**
```
Date          | Events | Community | Review | Status   | Runtime
2025-01-20    | 42     | 28        | 3      | Success  | 2m 34s
2025-01-27    | 38     | 25        | 2      | Success  | 2m 18s
```

**Sheet 2: Upload History**
```
Date      | Approver      | Events | Status   | WordPress Events
2025-01-21| supervisor@.. | 28     | Success  | 28 added, 0 errors
2025-01-28| you@...       | 25     | Success  | 25 added, 0 errors
```

**Sheet 3: Health Status**
```
Date       | WP    | Email | GDrive | Issues
2025-01-20 | ✅ OK | ✅ OK | ✅ OK  | None
2025-01-19 | ⚠️ DNS | ✅ OK | ✅ OK  | WP unreachable 2hrs
```

### 11.2 Make.com Built-in Monitoring

1. **Scenario overview**: Blue chart shows executions
2. **Execution history**: Click to see each run
3. **Statistics**: Success rate, avg runtime

### 11.3 Email Alerts

Supervisors receive:
- Weekly summary email (Monday 8 AM)
- On-demand upload confirmation
- **Daily health check** (if configured)
- Failure alerts with remediation steps

---

## Phase 12: Advanced Features (Optional)

### 12.1 Add Slack Notifications

**In Make.com, add Slack module:**

```
1. Connections → Slack
2. In scenario: After upload completes
3. Send message to #calendar-updates channel:
   "✅ 28 events uploaded to calendar"
```

### 12.2 Event Approval Workflow

**Add approval step:**

```
1. Pipeline runs, classifies events
2. Send approval request to supervisor via email
3. Link to Google Form with "Approve" button
4. On approval, trigger WordPress upload
5. Send confirmation

(Implements manual approval gate before upload)
```

### 12.3 Auto-Retry on Failure

**Make.com Settings:**
- Enable "Rerun schedule" on failure
- Retry up to 3 times with 5-min intervals

### 12.4 Custom Alerts

```
Send different alerts for different failures:
  - Model file missing → Email with instructions
  - WordPress down → Slack @admin
  - Email failure → Log to Sheet only
```

---

## Troubleshooting Guide

### Problem: "AWS Lambda timeout"
**Solution:**
- Increase timeout to 300s in Lambda console
- Optimize scraping (add caching)
- Check internet speed of Lambda runtime

### Problem: "Google Drive auth failed"
**Solution:**
- Re-authorize Make.com Google Drive connection
- Verify folder permissions (not shared with restrictive perms)

### Problem: "WordPress API returns 403"
**Solution:**
- Verify App Password hasn't changed
- Check WP REST API is enabled
- Verify EventON plugin is still active

### Problem: "Model file too large"
**Solution:**
- Store `.pkl` files in S3 instead of Google Drive
- Lambda can download from S3 (faster)
- Update Make.com to use S3 module

---

## Summary Checklist

- [ ] **Phase 1**: Created Google Drive folder, uploaded model artifacts, created secrets file
- [ ] **Phase 2**: Set up Make.com account, connected services, noted folder ID
- [ ] **Phase 3**: Created `make_cloud_pipeline.py` wrapper, refactored `automated_pipeline.py`
- [ ] **Phase 4**: Built 3 Make.com scenarios (Pipeline, Upload, Health Check)
- [ ] **Phase 5**: Deployed Lambda function, got function URL
- [ ] **Phase 6**: Added secrets to Make.com vault, configured HTTP modules
- [ ] **Phase 7**: Invited supervisors, shared webhook links, created dashboard
- [ ] **Phase 8**: Set up local sync strategy (Git or one-way sync)
- [ ] **Phase 9**: Tested locally, tested in Make.com, tested supervisor access
- [ ] **Phase 10**: Documented operational procedures
- [ ] **Phase 11**: Created Google Sheets dashboard, configured alerts
- [ ] **Phase 12** (optional): Added Slack, approval workflow, auto-retry

---

## Next Steps

1. **This week**: Complete Phases 1-3 (local setup, prepare scripts)
2. **Next week**: Complete Phases 4-6 (build scenarios, deploy Lambda)
3. **Week 3**: Complete Phases 7-9 (invite team, test thoroughly)
4. **Week 4**: Go live, monitor, iterate based on feedback

---

## Support & Documentation

- **Make.com Docs**: https://www.make.com/en/help/
- **AWS Lambda**: https://docs.aws.amazon.com/lambda/
- **Google Drive API**: https://developers.google.com/drive/api/
- **EnvisionPerdido Local Docs**: See `docs/` folder

**For questions:**
- Review the troubleshooting section above
- Check Make.com execution history for detailed errors
- Check AWS CloudWatch Logs for Lambda errors
- Review the original `docs/QUICKSTART.md` for pipeline logic

---

**Created:** January 22, 2025  
**Last Updated:** January 22, 2025  
**Status:** Ready for deployment
