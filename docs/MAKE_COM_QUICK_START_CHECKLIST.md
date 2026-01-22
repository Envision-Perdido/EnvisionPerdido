# Make.com Migration - Quick Start Checklist

## Week 1: Preparation & Setup (Days 1-5)

### Day 1: Documentation & Planning
- [ ] Read [MAKE_COM_MIGRATION_GUIDE.md](MAKE_COM_MIGRATION_GUIDE.md) completely
- [ ] Understand the 3-tier architecture: Make.com → Lambda → Local PC (backup)
- [ ] Identify supervisor email addresses for team access
- [ ] Verify WordPress site is ready for API integration

### Day 2: Local Preparation
- [ ] Create Google Drive folder structure:
  ```
  Your Drive/
  └── EnvisionPerdido/
      ├── models/
      │   ├── event_classifier_model.pkl
      │   └── event_vectorizer.pkl
      ├── config/
      │   └── image_keyword_config.json
      ├── outputs/
      └── cache/
  ```

- [ ] **CRITICAL: Upload model files to Google Drive** (one-time, manual)
  - [ ] Find and copy `event_classifier_model.pkl` from local PC
  - [ ] Find and copy `event_vectorizer.pkl` from local PC
  - [ ] Verify files are readable in Drive

- [ ] Run local test to confirm everything works:
  ```powershell
  cd C:\Users\scott\UWF-Code\EnvisionPerdido
  .\.venvEnvisionPerdido\Scripts\Activate.ps1
  
  $env:SKIP_WP_UPLOAD = "true"
  python scripts\automated_pipeline.py
  ```

### Day 3: Create Make.com Account
- [ ] Sign up at https://make.com (free tier)
- [ ] Verify email
- [ ] Create organization (e.g., "EnvisionPerdido")
- [ ] Note your organization ID (in URL: make.com/org/{ORG_ID})

### Day 4: Connect Services
- [ ] **Google Drive**: Connections → Authorize Google Drive
  - [ ] Go to your Google Drive
  - [ ] Find the `EnvisionPerdido` folder you created
  - [ ] Copy folder ID from URL: `https://drive.google.com/drive/folders/{FOLDER_ID}`
  - [ ] Save it (you'll need it for Make.com scenarios)

- [ ] **Gmail**: Connections → Authorize Gmail
  - [ ] Use your configured sender email
  - [ ] Complete OAuth flow

- [ ] **WordPress**: Test connection locally first
  ```powershell
  python scripts\test_wp_auth.py
  ```

### Day 5: Generate Deployment Artifacts
- [ ] Run the deployment helper:
  ```powershell
  cd C:\Users\scott\UWF-Code\EnvisionPerdido
  
  # Prepare Lambda package
  python scripts\make_deploy_helper.py --all
  ```

- [ ] Verify output:
  ```
  ✅ lambda_deployment/lambda_function.zip created
  ✅ scripts/make_env_template.json (safe to commit)
  ✅ scripts/make_env_secrets.json (do NOT commit)
  ✅ .gitignore updated
  ```

---

## Week 2: AWS Lambda & Make.com Setup (Days 6-10)

### Day 6: Create AWS Account & IAM Role
- [ ] Go to https://aws.amazon.com (free tier available)
- [ ] Create account
- [ ] Install AWS CLI: https://aws.amazon.com/cli/
- [ ] Configure credentials:
  ```powershell
  aws configure
  # Enter: Access Key ID, Secret Access Key, Region (us-east-1), Output (json)
  ```

- [ ] Create Lambda execution role (one-time):
  ```powershell
  # Run the AWS CLI commands from the migration guide (Phase 5.2)
  # This creates a role with basic Lambda permissions
  ```

### Day 7: Deploy Lambda Function
- [ ] Deploy from your prepared ZIP:
  ```powershell
  cd C:\Users\scott\UWF-Code\EnvisionPerdido
  
  # Create function (replace YOUR_ACCOUNT_ID)
  aws lambda create-function `
    --function-name EnvisionPerdido-Pipeline `
    --runtime python3.11 `
    --role arn:aws:iam::YOUR_ACCOUNT_ID:role/lambda-execution-role `
    --handler lambda_handler.lambda_handler `
    --zip-file fileb://lambda_deployment/lambda_function.zip `
    --timeout 300 `
    --memory-size 512
  ```

- [ ] Create Function URL:
  ```powershell
  aws lambda create-function-url-config `
    --function-name EnvisionPerdido-Pipeline `
    --auth-type NONE `
    --cors "AllowOrigins=*,AllowMethods=POST,AllowHeaders=*"
  ```

- [ ] Get Function URL:
  ```powershell
  aws lambda get-function-url-config --function-name EnvisionPerdido-Pipeline
  
  # Copy the FunctionUrl (looks like https://abcdef123xyz.lambda-url.us-east-1.on.aws/)
  ```

- [ ] Save Function URL to: `scripts/make_env_secrets.json` → `AWS_LAMBDA_URL`

### Day 8: Add Secrets to Make.com
- [ ] In Make.com Dashboard: **Organization** → **Secrets**
- [ ] Create 8 secrets (one at a time):
  ```
  ✅ SENDER_EMAIL
  ✅ EMAIL_PASSWORD
  ✅ RECIPIENT_EMAIL
  ✅ WP_SITE_URL
  ✅ WP_USERNAME
  ✅ WP_APP_PASSWORD
  ✅ GOOGLE_DRIVE_FOLDER_ID
  ✅ AWS_LAMBDA_URL
  ```

- [ ] Test secret retrieval:
  - [ ] In a scenario, try using `{{secrets.SENDER_EMAIL}}`
  - [ ] If it appears in autocomplete, secrets are ready

### Day 9: Build Scenario 1 - Weekly Pipeline
- [ ] Create new scenario: **Create** → **New Scenario**
- [ ] Name: `EnvisionPerdido - Weekly Event Pipeline`
- [ ] Add modules (following guide Phase 4.1):
  ```
  1. Scheduler (Weekly, Monday 8 AM UTC)
  2. Set Variables (SMTP_SERVER, SENDER_EMAIL, etc.)
  3. HTTP - POST to AWS Lambda
  4. Gmail - Send success email
  5. Google Drive - Upload results
  ```

- [ ] Test: Click **Run Once** and check execution history
- [ ] Expected result:
  ```json
  {
    "status": "success",
    "events_classified": 42,
    "community_events": 28
  }
  ```

### Day 10: Build Scenario 2 & 3 - Upload & Health Check
- [ ] Create Scenario 2: `EnvisionPerdido - Manual Upload Trigger`
  - [ ] Trigger: Webhook
  - [ ] Get webhook URL
  - [ ] Test with curl or Postman

- [ ] Create Scenario 3: `EnvisionPerdido - Daily Health Monitor`
  - [ ] Trigger: Daily schedule
  - [ ] Run health checks
  - [ ] Send alerts on failure

---

## Week 3: Testing & Team Setup (Days 11-15)

### Day 11: Dry Run Testing
- [ ] Run Scenario 1 manually: **Run Once**
- [ ] Check Make.com execution history for errors
- [ ] Check your email inbox for pipeline results
- [ ] Verify Google Drive has CSV output

- [ ] If errors, debug:
  - [ ] Click failed execution → View module details
  - [ ] Check AWS CloudWatch Logs: `aws logs tail /aws/lambda/EnvisionPerdido-Pipeline`
  - [ ] Fix code or configuration

### Day 12: Test Supervisor Access
- [ ] Prepare supervisor list (e.g., 2 supervisors)
- [ ] Share webhook URL with each supervisor:
  ```
  https://make.com/webhooks/[webhook_id]/invoke?action=upload
  ```

- [ ] Ask one supervisor to click it
- [ ] Verify they receive confirmation email

- [ ] Share Google Sheets dashboard link (read-only)

### Day 13: Create Monitoring Dashboard
- [ ] Create Google Sheets: `EnvisionPerdido Execution Log`
- [ ] Create 3 sheets:
  - Pipeline Runs (Date, Events, Status, Runtime)
  - Upload History (Date, Approver, Events, Status)
  - Health Checks (Date, WP, Email, GDrive, Issues)

- [ ] In Scenario 1, add module:
  - **Google Sheets** → **Append a row**
  - Log each successful run

- [ ] Share sheet with supervisors (read-only)

### Day 14: Configure Email Alerts
- [ ] Edit Scenario 1 → Add error handler
- [ ] If pipeline fails:
  - [ ] Send alert to RECIPIENT_EMAIL
  - [ ] Include error details
  - [ ] Suggest troubleshooting steps

- [ ] Edit Scenario 3 (Health Check):
  - [ ] If check fails, send alert
  - [ ] Email subject: "⚠️ EnvisionPerdido Health Alert"

### Day 15: Document & Train Team
- [ ] Create operations document:
  - [ ] What supervisors should expect weekly
  - [ ] How to trigger upload manually
  - [ ] What to do if something fails
  - [ ] Contact info (you)

- [ ] Send to supervisors:
  ```
  Subject: EnvisionPerdido Cloud Migration Complete ✅
  
  Hi team,
  
  The event pipeline has been moved to Make.com for 24/7 operation.
  
  Weekly workflow:
  1. Monday 8 AM - Automatic pipeline runs
  2. You receive email with results
  3. Click "Upload" link if approved
  4. Dashboard: [Google Sheets link]
  
  Questions? Contact me.
  ```

---

## Week 4: Go Live & Optimize (Days 16-20)

### Day 16: Enable Scheduler
- [ ] In Scenario 1: **Scheduling** → Enable scheduler
- [ ] Verify first run Monday 8 AM UTC
- [ ] Monitor execution history

### Day 17: Monitor First Live Run
- [ ] Check email inbox Monday morning
- [ ] Review Google Drive outputs
- [ ] Check Google Sheets dashboard
- [ ] Confirm supervisors received email

### Day 18: Optimize Performance
- [ ] Review Lambda execution time in CloudWatch
- [ ] If slow, consider:
  - [ ] Caching scraped data
  - [ ] Pre-loading model artifacts to Lambda `/tmp`
  - [ ] Increasing Lambda memory (affects CPU)

- [ ] Check Make.com execution time
- [ ] Optimize module order if needed

### Day 19: Backup & Version Control
- [ ] Commit all safe files to git:
  ```powershell
  git add scripts/make_cloud_pipeline.py
  git add scripts/make_health_check.py
  git add scripts/make_deploy_helper.py
  git add scripts/make_env_template.json
  git add .github/MAKE_COM_MIGRATION_GUIDE.md
  
  git commit -m "Feat: Add Make.com CI/CD integration"
  ```

- [ ] DO NOT commit:
  - `scripts/make_env_secrets.json`
  - `lambda_deployment/`

- [ ] Tag version: `git tag v2.0-make-deployment`

### Day 20: Handoff to Supervisors
- [ ] Schedule team meeting
- [ ] Demo:
  - [ ] Show Make.com dashboard
  - [ ] Explain weekly workflow
  - [ ] Test manual webhook trigger
  - [ ] Show Google Sheets dashboard

- [ ] Provide documentation:
  - [ ] Quickstart guide (1-page)
  - [ ] Troubleshooting tips
  - [ ] Your contact info

---

## Post-Go-Live Maintenance

### Daily
- [ ] Check email for alerts
- [ ] Quick look at Google Sheets dashboard (if available)

### Weekly (After Monday 8 AM run)
- [ ] Verify pipeline completed
- [ ] Review event counts
- [ ] Check for any errors in Make.com

### Monthly
- [ ] Review Make.com execution logs
- [ ] Check Lambda cost (usually free tier)
- [ ] Consider updating model if new training data available

---

## Troubleshooting Quick Links

| Issue | Solution |
|-------|----------|
| Lambda timeout | Increase timeout to 300s, check internet speed |
| Google Drive auth failed | Re-authorize in Make.com → Connections |
| WordPress connection error | Verify app password, check WP REST API enabled |
| Model file missing | Upload .pkl files to Google Drive, verify paths |
| Email not sending | Verify Gmail app password, check SMTP settings |

---

## Final Checklist - Ready to Go Live?

- [ ] All 3 AWS Lambda tests passed
- [ ] All 3 Make.com scenarios created and tested
- [ ] Supervisors can access webhook and receive emails
- [ ] Google Sheets dashboard created
- [ ] Documentation provided to team
- [ ] Git repository updated with new code
- [ ] Model files backed up to Google Drive
- [ ] Scheduler enabled on all scenarios

---

**Status**: Ready for deployment  
**Start Date**: [Your date]  
**Go Live Date**: [Target date - typically Week 4]  
**Contact**: You  

---

For detailed information, see [MAKE_COM_MIGRATION_GUIDE.md](MAKE_COM_MIGRATION_GUIDE.md)
