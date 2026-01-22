# Make.com Migration - Architecture & Decision Matrix

## System Architecture Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                        EXTERNAL SERVICES                           │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐ │
│  │   Perdido Coop   │  │   WordPress      │  │   Gmail / SMTP   │ │
│  │   (Web Scrape)   │  │   EventON        │  │   (Email)        │ │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘ │
│         ↓                      ↑                      ↑             │
└────────────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────────┐
│                    MAKE.COM CLOUD PLATFORM                         │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Scenario 1: Weekly Pipeline (Scheduler → Lambda)           │  │
│  │  ├─ Trigger: Monday 8 AM UTC                                │  │
│  │  ├─ Call AWS Lambda Function                                │  │
│  │  ├─ Download models from Google Drive                       │  │
│  │  ├─ Execute classification pipeline                         │  │
│  │  ├─ Upload results to Google Drive                          │  │
│  │  └─ Send email summary                                      │  │
│  └──────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Scenario 2: Manual Upload (Webhook Trigger)                │  │
│  │  ├─ Trigger: Supervisor clicks webhook link                 │  │
│  │  ├─ Get latest CSV from Google Drive                        │  │
│  │  ├─ Call WordPress upload function                          │  │
│  │  └─ Send confirmation email                                 │  │
│  └──────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Scenario 3: Daily Health Check                             │  │
│  │  ├─ Trigger: Daily 9 AM UTC                                 │  │
│  │  ├─ Test WordPress, Gmail, Google Drive                     │  │
│  │  └─ Send alert if any service down                          │  │
│  └──────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Secrets Vault: Store sensitive credentials                 │  │
│  │  ├─ SENDER_EMAIL, EMAIL_PASSWORD                            │  │
│  │  ├─ WP_USERNAME, WP_APP_PASSWORD                            │  │
│  │  └─ AWS_LAMBDA_URL, GOOGLE_DRIVE_FOLDER_ID                 │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────────┐
│                    AWS LAMBDA (Python Runtime)                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Lambda Function: EnvisionPerdido-Pipeline                  │  │
│  │  ├─ Handler: lambda_handler.py                              │  │
│  │  ├─ Runtime: Python 3.11                                    │  │
│  │  ├─ Memory: 512 MB                                          │  │
│  │  ├─ Timeout: 300 seconds                                    │  │
│  │  └─ Executes:                                               │  │
│  │     ├─ make_cloud_pipeline.py (wrapper)                     │  │
│  │     ├─ automated_pipeline.py (main logic)                   │  │
│  │     ├─ Envision_Perdido_DataCollection.py (scraper)         │  │
│  │     └─ event_normalizer.py (processing)                     │  │
│  └──────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  CloudWatch Logs: Execution history and debugging           │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
                ↓                              ↓
     ┌──────────────────────┐    ┌──────────────────────┐
     │   GOOGLE DRIVE       │    │  GOOGLE SHEETS       │
     │  Outputs &           │    │  (Dashboard)         │
     │  Model Artifacts     │    │  Pipeline Runs       │
     │  - .pkl files        │    │  Upload History      │
     │  - CSVs              │    │  Health Status       │
     │  - Configs           │    │  Error Log           │
     └──────────────────────┘    └──────────────────────┘
                ↓                              ↓
         ┌──────────────────────────────────────┐
         │   SUPERVISORS / STAKEHOLDERS         │
         │  ├─ Email notifications (weekly)     │
         │  ├─ Webhook links (manual trigger)   │
         │  └─ Shared dashboard (monitoring)    │
         └──────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────┐
│                    YOUR LOCAL PC (Backup/Reference)                │
│  ├─ Git repository (version control)                              │
│  ├─ Local copy of code (can modify & push updates)                │
│  ├─ Scheduled tasks (optional - for redundancy)                   │
│  └─ Model artifacts (also on Google Drive)                        │
└────────────────────────────────────────────────────────────────────┘
```

---

## Decision Matrix: Local vs. Cloud vs. Hybrid

### When to keep running locally:

**PROS**
- Direct control over execution
- Can modify/debug easily
- Familiar environment
- No cloud costs

**CONS**
- Requires PC to be on 24/7
- No automated failover
- Hard to share with supervisors
- Difficult to scale

### When to move to Make.com:

**PROS**
- 24/7 execution without PC
- Supervisors can monitor/trigger via web dashboard
- Email alerts and notifications
- Built-in logging and history
- Easy to add new workflows
- Scale horizontally (add more scenarios)
- Automated retry on failure

**CONS**
- Requires AWS account + costs ($0-10/month typically)
- Learning curve for Make.com
- Secrets stored outside your control
- Internet dependency (but more reliable than local)

### Hybrid Approach (Recommended):

**YOU CHOOSE:**

1. **Primary**: Make.com Cloud (your supervisors access this)
   - Runs all automated workflows
   - Always available
   - Shared with team

2. **Backup**: Local PC (your personal development copy)
   - Mirror of Make.com setup
   - For testing changes
   - Can manually trigger if cloud fails
   - Source of truth for code (git)

**This is the approach this guide implements.**

---

## Cost Analysis

### AWS Lambda (Monthly)

```
Requests: 1 run/week × 52 weeks = 52 invocations
Execution time: ~3 minutes per run × 52 = 156 minutes
Memory: 512 MB

Free tier: 1M requests + 400K GB-seconds per month
Cost: FREE (well under free tier)

Occasional cost: If >1M requests, ~$0.20 per 1M requests
```

### Make.com (Monthly)

```
Free plan: Up to 1,000 operations/month
1 pipeline run (7 modules) = ~7 operations
52 runs × 7 = 364 operations

Plus occasional manual uploads:
~100-200 operations

Total: ~500 operations/month = FREE tier

If upgrade needed: Pro plan = $10.99/month
```

### Google Drive / Gmail / Sheets

```
Gmail: FREE (using existing account)
Google Drive: FREE (15 GB included, not using much)
Google Sheets: FREE (unlimited)
```

### **Total Monthly Cost: $0-11** (depending on volume)

---

## Security & Compliance

### Data at Rest

| Data | Location | Encryption | Access |
|------|----------|-----------|--------|
| Model artifacts (.pkl) | Google Drive | Google encryption | Make.com + You |
| Credentials | Make.com Secrets | AES-256 | Make.com only |
| Pipeline outputs (CSV) | Google Drive | Google encryption | Make.com + Supervisors |
| Scraped events | Google Drive temp | Google encryption | Make.com only |
| Logs | AWS CloudWatch | AWS encryption | You (AWS account) |

### Data in Transit

| Connection | Protocol | Encrypted |
|-----------|----------|-----------|
| Make.com → AWS Lambda | HTTPS | ✅ Yes |
| Lambda → Google Drive | HTTPS | ✅ Yes |
| Lambda → WordPress | HTTPS (HTTP Basic Auth) | ✅ Yes |
| Lambda → Gmail | HTTPS (SMTP TLS) | ✅ Yes |
| Make.com → Supervisor | Email | ✅ Yes |

### Access Control

```
┌─────────────────────────────────────┐
│ You (Developer/Admin)               │
├─────────────────────────────────────┤
│ ✅ Can edit Make.com scenarios      │
│ ✅ Can view execution history       │
│ ✅ Can manually trigger workflows   │
│ ✅ Can manage secrets vault         │
│ ✅ Can invite/remove supervisors    │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ Supervisors (Viewer Access)         │
├─────────────────────────────────────┤
│ ✅ Can view scenario details        │
│ ✅ Can see execution history        │
│ ✅ Can click webhook to upload      │
│ ✅ Cannot edit scenarios            │
│ ✅ Cannot view secrets              │
│ ✅ Cannot modify configuration      │
└─────────────────────────────────────┘
```

---

## Disaster Recovery Plan

### Scenario: Make.com Service Down (Very Rare)

**Recovery Time: <1 hour**

```
Step 1: Check Make.com status page (status.make.com)
Step 2: If confirmed outage, switch to backup
Step 3: Run local pipeline:
  
  cd C:\Users\scott\UWF-Code\EnvisionPerdido
  .\.venvEnvisionPerdido\Scripts\Activate.ps1
  python scripts\automated_pipeline.py
  
Step 4: Manually upload results to Google Drive
Step 5: Notify supervisors (email)
Step 6: When Make.com recovers, resume automatic scheduling
```

### Scenario: AWS Lambda Function Deleted/Broken

**Recovery Time: <30 minutes**

```
Step 1: Check CloudWatch Logs for error details
Step 2: If unrecoverable:
  
  # Redeploy from your local package
  python scripts\make_deploy_helper.py --prepare
  
  aws lambda update-function-code \
    --function-name EnvisionPerdido-Pipeline \
    --zip-file fileb://lambda_deployment/lambda_function.zip
  
Step 3: Test: Make.com scenario → Run Once
Step 4: Verify execution succeeded
```

### Scenario: Google Drive Storage Full

**Recovery Time: <5 minutes**

```
Step 1: Check Google Drive storage (drive.google.com/settings/storage)
Step 2: Delete old outputs or archive to zip
Step 3: Update Make.com scenario to use different folder if needed
Step 4: Resume execution
```

### Scenario: WordPress Site Down

**Recovery Time: Depends on WordPress provider**

```
The pipeline will:
- ✅ Still scrape and classify (works without WordPress)
- ✅ Still send email with results
- ❌ Skip WordPress upload (expected behavior)

You can:
- Wait for WordPress to recover
- Click webhook manually when ready
- Or manually upload from Google Drive
```

---

## Performance Benchmarks

### Typical Pipeline Execution

```
Activity                    Time    % of Total
─────────────────────────────────────────────
Scrape Perdido website      ~45s    30%
Classify with ML model      ~60s    40%
Send email                  ~10s    7%
Upload to WordPress         ~30s    20%
─────────────────────────────────────────
TOTAL                       ~145s   100%
(~2.5 minutes)
```

### How to Monitor Performance

1. **Make.com Dashboard**: Shows execution time for each scenario
2. **AWS CloudWatch**: Click on Make.com execution → View Lambda logs
3. **Google Sheets Dashboard**: Log execution times weekly

### Performance Optimization Tips

| Issue | Solution |
|-------|----------|
| Slow scraping | Add caching, increase Lambda memory |
| Slow model | Consider smaller model or feature reduction |
| Email delays | Gmail is usually instant, check auth |
| WordPress timeout | Increase Lambda timeout, check WP server |

---

## Migration Checklist by Phase

### Phase 1: Preparation ✅
- [ ] Google Drive folder created
- [ ] Model files uploaded
- [ ] Secrets template created
- [ ] Local test run successful

### Phase 2: Cloud Services ✅
- [ ] Make.com account created
- [ ] Services connected (Google Drive, Gmail)
- [ ] Secrets vault configured

### Phase 3: Code Refactoring ✅
- [ ] `make_cloud_pipeline.py` created
- [ ] `make_health_check.py` created
- [ ] `make_deploy_helper.py` created

### Phase 4: Make.com Scenarios ✅
- [ ] Scenario 1: Weekly Pipeline (built & tested)
- [ ] Scenario 2: Manual Upload (built & tested)
- [ ] Scenario 3: Health Check (built & tested)

### Phase 5: AWS Lambda ✅
- [ ] Lambda function deployed
- [ ] Function URL created
- [ ] Environment variables configured

### Phase 6: Testing ✅
- [ ] Local dry-run successful
- [ ] Make.com dry-run successful
- [ ] Supervisor access verified
- [ ] Email notifications working

### Phase 7: Documentation ✅
- [ ] Operations guide created
- [ ] Team trained
- [ ] Contact info shared

### Phase 8: Go Live ✅
- [ ] Scheduler enabled
- [ ] First run monitored
- [ ] Supervisors notified

### Phase 9: Optimization (Ongoing)
- [ ] Performance monitored
- [ ] Issues logged and fixed
- [ ] Documentation updated

---

## Support & Escalation

### You Have an Issue...

```
Is it about Make.com?
├─ Yes → Check Make.com documentation: https://www.make.com/en/help/
├─ Read: Scenarios, Modules, Connections, Secrets
└─ Still stuck? → Make.com support chat (in dashboard)

Is it about AWS Lambda?
├─ Yes → Check AWS documentation: https://docs.aws.amazon.com/lambda/
├─ Read: CloudWatch Logs, Lambda configuration, error codes
└─ Still stuck? → AWS support (requires support plan)

Is it about your Python code?
├─ Yes → Check the code in scripts/
├─ Review: make_cloud_pipeline.py, automated_pipeline.py
├─ Run locally to debug
└─ Fix and re-deploy: make_deploy_helper.py --prepare

Is it about WordPress integration?
├─ Yes → Check docs/WORDPRESS_INTEGRATION_GUIDE.md
├─ Test locally: python scripts/test_wp_auth.py
└─ Verify: App password, REST API enabled, EventON plugin active
```

### When You Need Help

**For quick issues** (Make.com syntax, AWS CLI):
- Search the respective service documentation
- Check execution history for error messages
- Review logs

**For application issues** (pipeline logic, classification):
- Test locally first (always works better)
- Check the original documentation in `docs/`
- Review the code changes you made

**For cloud integration issues**:
- Verify credentials are correct
- Check service is accessible (health check)
- Review Make.com execution module details

---

## Next Steps

1. **This week**: Complete Preparation Phase (Days 1-5)
   - Read all documentation
   - Create Google Drive structure
   - Test locally

2. **Next week**: Complete Cloud Setup (Days 6-10)
   - Create AWS account
   - Deploy Lambda
   - Build Make.com scenarios

3. **Week 3**: Testing & Team Setup (Days 11-15)
   - Test thoroughly
   - Invite supervisors
   - Create dashboards

4. **Week 4**: Go Live (Days 16-20)
   - Enable scheduler
   - Monitor first run
   - Optimize

---

## FAQ

**Q: Can I still run the pipeline locally?**
A: Yes! The local copy stays as a backup. You can run `automated_pipeline.py` anytime.

**Q: What if my PC crashes?**
A: Make.com keeps running (it's cloud-based). You can restore from git when your PC comes back.

**Q: Can supervisors directly edit events?**
A: No, they can only view and trigger uploads. You maintain control of the data pipeline.

**Q: What if the model needs retraining?**
A: Retrain locally, upload new .pkl files to Google Drive. Lambda will use the new versions.

**Q: How much does this cost?**
A: Typically free (AWS free tier + Make.com free tier). Rarely exceeds $10/month.

**Q: Can I undo this and go back to local-only?**
A: Yes, but there's no reason to. You'll keep the local copy anyway.

---

**Version**: 2.0 (Make.com Edition)  
**Last Updated**: January 22, 2025  
**Status**: Ready for Deployment
