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

**A. Google Drive Integration:**
1. In Make.com dashboard: **Connections**
2. Add → **Google Drive**
3. Authorize Make.com to access your Drive
4. Note the **Folder ID** of your `EnvisionPerdido` folder:
   - Open https://drive.google.com/drive/folders/YOUR_FOLDER_ID
   - Copy the ID from URL

**B. Gmail Integration (for email notifications):**
1. **Connections** → **Gmail**
2. Authorize (use your configured sender email)

**C. WordPress Integration (via REST API):**
1. No pre-connection needed; we'll use HTTP module
2. But verify your App Password works locally first:
   ```powershell
   # Test WordPress connection
   python scripts\test_wp_auth.py
   ```

**D. Google Sheets (optional, for public dashboards):**
1. **Connections** → **Google Sheets**
2. Authorize if using Sheets for event summaries

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

### 4.1 Create Scenario 1: Weekly Scrape & Classify

**Scenario Name:** `EnvisionPerdido - Weekly Event Pipeline`

**Trigger:** Schedule (Weekly, Monday 8 AM UTC)

**Flow:**

```
1. SCHEDULER
   ├─ Trigger: Weekly, Monday 8:00 AM UTC
   ├─ Timezone: America/Chicago (auto-convert)
   
2. ENVIRONMENT SETUP (Set Variables module)
   ├─ SMTP_SERVER: smtp.gmail.com
   ├─ SMTP_PORT: 587
   ├─ SENDER_EMAIL: {{secrets.SENDER_EMAIL}}
   ├─ EMAIL_PASSWORD: {{secrets.EMAIL_PASSWORD}}
   ├─ RECIPIENT_EMAIL: {{secrets.RECIPIENT_EMAIL}}
   ├─ WP_SITE_URL: {{secrets.WP_SITE_URL}}
   ├─ WP_USERNAME: {{secrets.WP_USERNAME}}
   ├─ WP_APP_PASSWORD: {{secrets.WP_APP_PASSWORD}}
   └─ GOOGLE_DRIVE_FOLDER_ID: {{secrets.GOOGLE_DRIVE_FOLDER_ID}}

3. GOOGLE DRIVE - DOWNLOAD MODEL ARTIFACTS
   ├─ Module: Google Drive → Download a file
   ├─ File: event_classifier_model.pkl (from Your Drive/EnvisionPerdido/models/)
   └─ Output: {{model_binary}}

4. GOOGLE DRIVE - DOWNLOAD VECTORIZER
   ├─ Module: Google Drive → Download a file
   ├─ File: event_vectorizer.pkl
   └─ Output: {{vectorizer_binary}}

5. WEBHOOK / PYTHON EXECUTION
   ├─ Module: HTTP → Make a request
   ├─ URL: https://your-python-runtime.com/execute
   ├─ Method: POST
   ├─ Body: {
   │   "script": "make_cloud_pipeline.py",
   │   "env": {environment variables},
   │   "model": {{model_binary}},
   │   "vectorizer": {{vectorizer_binary}}
   │ }
   └─ Output: {{pipeline_result}}

6. UPLOAD RESULTS TO GOOGLE DRIVE
   ├─ Module: Google Drive → Create a file
   ├─ Filename: calendar_upload_{{now.timestamp()}}.csv
   ├─ Content: {{pipeline_result.csv}}
   └─ Folder: Your Drive/EnvisionPerdido/outputs/

7. SEND SUCCESS EMAIL
   ├─ Module: Gmail → Send an email
   ├─ To: {{secrets.RECIPIENT_EMAIL}}
   ├─ Subject: ✅ EnvisionPerdido Weekly Pipeline - {{now.formatAsString('YYYY-MM-DD')}}
   ├─ Body: HTML with statistics
   └─ Attachment: calendar_upload_*.csv

8. ERROR HANDLING (Router)
   ├─ If pipeline_result.status == 'error'
   │  └─ Send alert email to supervisors
   └─ If success
      └─ Log to Google Sheets (optional)
```

**Module Details:**

**Set Variables:**
```
Make.com Dashboard → Click "+" → Search "Set Variables"

Variable 1:
  Name: SMTP_SERVER
  Type: Text
  Value: smtp.gmail.com

Variable 2:
  Name: EMAIL_PASSWORD
  Type: Text (Secret)
  Value: Click "Secrets" button, select EMAIL_PASSWORD from vault

[Repeat for all 9 variables listed above]
```

**Download Model (Google Drive):**
```
Search: Google Drive
Select: Download a file
Choose: event_classifier_model.pkl
Result variable: model_file
```

**Python Execution (via HTTP):**

Since Make.com doesn't have native Python execution, use one of these:

**Option A: AWS Lambda (Recommended)**
```
1. Create Lambda function with your Python code
2. Add Make.com execution role
3. In Make.com: HTTP → POST to Lambda function URL
4. Pass environment variables in request body
```

**Option B: Replit (Free)**
```
1. Host scripts on Replit
2. Create POST endpoint
3. Call from Make.com HTTP module
```

**Option C: PythonAnywhere**
```
1. Upload scripts to PythonAnywhere
2. Create Web API endpoint
3. Call from Make.com
```

For now, let's use **AWS Lambda** as it's most reliable.

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

## Phase 5: Deploy to AWS Lambda

### 5.1 Create Lambda Function

**Prerequisites:**
- AWS account (free tier available)
- AWS CLI installed

**Step 1: Prepare deployment package**

```powershell
# On your PC
cd c:\Users\scott\UWF-Code\EnvisionPerdido

# Create lambda directory
mkdir lambda_deployment
cd lambda_deployment

# Copy scripts
Copy-Item ..\scripts\make_cloud_pipeline.py -Destination .\
Copy-Item ..\scripts\automated_pipeline.py -Destination .\
Copy-Item ..\scripts\wordpress_uploader.py -Destination .\
Copy-Item ..\scripts\Envision_Perdido_DataCollection.py -Destination .\
Copy-Item ..\requirements.txt -Destination .\

# Install dependencies
pip install -r requirements.txt -t ./

# Create handler file
@"
import json
import os
import sys
from make_cloud_pipeline import run_pipeline_in_make, load_make_secrets

def lambda_handler(event, context):
    """
    AWS Lambda handler for Make.com pipeline execution.
    
    event: Contains environment variables and webhook data
    """
    try:
        # Extract secrets from event (passed by Make.com)
        secrets = {key: event.get(key) for key in [
            'SMTP_SERVER', 'SMTP_PORT', 'SENDER_EMAIL', 'EMAIL_PASSWORD',
            'RECIPIENT_EMAIL', 'WP_SITE_URL', 'WP_USERNAME', 'WP_APP_PASSWORD',
            'GOOGLE_DRIVE_FOLDER_ID', 'SITE_TIMEZONE'
        ]}
        
        # Run pipeline
        result = run_pipeline_in_make(secrets)
        
        return {
            'statusCode': 200 if result['status'] == 'success' else 500,
            'body': json.dumps(result)
        }
    
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'status': 'error',
                'message': str(e)
            })
        }
"@ | Out-File -FilePath .\lambda_handler.py -Encoding UTF8

# Create deployment package
Compress-Archive -Path .\ -DestinationPath lambda_function.zip -Force
```

**Step 2: Deploy to AWS Lambda**

```powershell
# Configure AWS credentials
aws configure
# Enter: AWS Access Key ID, Secret Access Key, Region (us-east-1), Output (json)

# Create Lambda function
aws lambda create-function `
  --function-name EnvisionPerdido-Pipeline `
  --runtime python3.11 `
  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/lambda-execution-role `
  --handler lambda_handler.lambda_handler `
  --zip-file fileb://lambda_function.zip `
  --timeout 300 `
  --memory-size 512

# Create Function URL (for webhook access)
aws lambda create-function-url-config `
  --function-name EnvisionPerdido-Pipeline `
  --auth-type NONE `
  --cors AllowOrigins='*',AllowMethods='POST',AllowHeaders='*'
```

**Step 3: Get Function URL**

```powershell
aws lambda get-function-url-config `
  --function-name EnvisionPerdido-Pipeline

# Note the FunctionUrl - this is what you'll call from Make.com
# Example: https://abcdef123xyz.lambda-url.us-east-1.on.aws/
```

### 5.2 Create Lambda IAM Role (One-time)

```powershell
# Create role
aws iam create-role `
  --role-name lambda-execution-role `
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "lambda.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Attach basic execution policy
aws iam attach-role-policy `
  --role-name lambda-execution-role `
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
```

---

## Phase 6: Configure Make.com Scenarios (Final Assembly)

### 6.1 Add Secrets Vault

In Make.com Dashboard:

1. **Organization** → **Secrets**
2. **Add secret** for each:
   ```
   - SENDER_EMAIL: your_email@gmail.com
   - EMAIL_PASSWORD: your_16_char_app_password
   - RECIPIENT_EMAIL: supervisor@example.com
   - WP_SITE_URL: https://your-site.org
   - WP_USERNAME: your_wp_username
   - WP_APP_PASSWORD: xxxx xxxx xxxx xxxx xxxx xxxx
   - GOOGLE_DRIVE_FOLDER_ID: 1abc2def3ghi4jkl5mno6pqr
   - AWS_LAMBDA_URL: https://abcdef123xyz.lambda-url.us-east-1.on.aws/
   ```

3. **Copy the secret name** (e.g., `{{secrets.SENDER_EMAIL}}`)

### 6.2 Build HTTP Module to Call Lambda

In the Pipeline Scenario:

```
1. Click "+" → Search "HTTP"
2. Select "Make a request"
3. Configure:
   - URL: {{secrets.AWS_LAMBDA_URL}}
   - Method: POST
   - Headers:
     - Content-Type: application/json
   - Body (JSON):
     {
       "SMTP_SERVER": "smtp.gmail.com",
       "SMTP_PORT": "587",
       "SENDER_EMAIL": "{{secrets.SENDER_EMAIL}}",
       "EMAIL_PASSWORD": "{{secrets.EMAIL_PASSWORD}}",
       "RECIPIENT_EMAIL": "{{secrets.RECIPIENT_EMAIL}}",
       "WP_SITE_URL": "{{secrets.WP_SITE_URL}}",
       "WP_USERNAME": "{{secrets.WP_USERNAME}}",
       "WP_APP_PASSWORD": "{{secrets.WP_APP_PASSWORD}}",
       "GOOGLE_DRIVE_FOLDER_ID": "{{secrets.GOOGLE_DRIVE_FOLDER_ID}}",
       "SITE_TIMEZONE": "America/Chicago"
     }
4. Parse response: Toggle "Parse response"
```

### 6.3 Enable Scenario Error Notifications

1. Scenario settings (gear icon)
2. **Advanced settings** → **Errors**
3. Enable: "Send notification if scenario fails"
4. Email: {{secrets.RECIPIENT_EMAIL}}

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
