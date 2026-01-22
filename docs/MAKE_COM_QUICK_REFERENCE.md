# Make.com Migration - Quick Reference Card

## 🚀 One-Page Overview

### What This Does
Moves your EnvisionPerdido pipeline from your PC to the cloud so it runs 24/7, supervisors can monitor it, and you keep your local copy for development.

---

## 📋 Quick Timeline

| Week | Days | Focus | Deliverables |
|------|------|-------|--------------|
| 1 | 1-5 | Prep | Google Drive setup, deployment package |
| 2 | 6-10 | Deploy | AWS Lambda, Make.com scenarios |
| 3 | 11-15 | Test | Dry runs, supervisor access |
| 4 | 16-20 | Go Live | Enable scheduler, monitor |

---

## 🎯 Architecture in 30 Seconds

```
Your PC (Local)
    ↓ (backup/dev)
Make.com Cloud (Control center)
    ↓ (executes)
AWS Lambda (Python runtime)
    ↓ (writes results)
Google Drive (Storage)
    ↓ (notifies)
Supervisors (Email + dashboard)
```

---

## 💰 Cost

| Item | Cost |
|------|------|
| AWS Lambda | FREE (first 1M requests/month) |
| Make.com | FREE (first 1,000 ops/month) |
| Google Drive | FREE (15 GB included) |
| **Total** | **$0** (usually) |

---

## 🔐 Security Checklist

- [ ] Secrets stored in Make.com vault (not code)
- [ ] HTTPS for all connections
- [ ] Supervisors can't edit, only view/trigger
- [ ] Execution history logged
- [ ] Health checks monitor all services

---

## 📁 Key Files

| File | Type | What It Does |
|------|------|-------------|
| MAKE_COM_MIGRATION_GUIDE.md | 📖 | 50-page detailed guide (START HERE) |
| MAKE_COM_QUICK_START_CHECKLIST.md | ✅ | Daily task list (USE FOR TRACKING) |
| make_cloud_pipeline.py | 💻 | Lambda handler (ready to use) |
| make_health_check.py | 🏥 | Service health monitor |
| make_deploy_helper.py | 🔧 | Builds deployment package |

---

## ⚡ 5-Minute Setup

```powershell
# 1. Prepare deployment package (creates ZIP for Lambda)
python scripts/make_deploy_helper.py --all

# 2. Follow printed instructions to deploy to AWS
# (Copy/paste AWS CLI commands)

# 3. Add secrets to Make.com vault
# (SENDER_EMAIL, EMAIL_PASSWORD, etc.)

# 4. Create 3 scenarios in Make.com
# (Weekly Pipeline, Manual Upload, Health Check)

# 5. Invite supervisors
# (Share webhook links + Google Sheets dashboard)

# Done! ✅
```

---

## 📊 What Supervisors See

### Email (Weekly, Monday 8 AM)
```
Subject: ✅ EnvisionPerdido Weekly Pipeline

📊 Results:
- Events scraped: 42
- Community events: 28
- Needs review: 3

Action: [Click to Upload] [View Dashboard]
```

### Dashboard (Google Sheets)
```
Date       | Events | Community | Status  | Notes
2025-01-20 | 42     | 28        | ✅ OK   | Normal
2025-01-27 | 38     | 25        | ✅ OK   | Fewer events
```

### Manual Trigger
```
Click webhook link anytime to upload latest results to WordPress
```

---

## 🛠️ Common Tasks

### Update Code After Deployment
```powershell
# 1. Test locally
python scripts/automated_pipeline.py

# 2. Rebuild package
python scripts/make_deploy_helper.py --prepare

# 3. Deploy to Lambda
aws lambda update-function-code `
  --function-name EnvisionPerdido-Pipeline `
  --zip-file fileb://lambda_deployment/lambda_function.zip
```

### Check Execution History
```
Make.com Dashboard → Click scenario → Execution History
(Shows: timestamp, duration, success/error, details)
```

### View Lambda Logs
```powershell
aws logs tail /aws/lambda/EnvisionPerdido-Pipeline --follow
```

### Manually Run Pipeline (Backup)
```powershell
cd C:\Users\scott\UWF-Code\EnvisionPerdido
.\.venvEnvisionPerdido\Scripts\Activate.ps1
python scripts/automated_pipeline.py
```

---

## ⚠️ Important Don'ts

```
❌ DON'T
- Commit secrets file to git
- Run pipeline from 2 places at once
- Share webhook URLs publicly
- Delete Lambda without backup

✅ DO
- Test locally before deploying
- Check Make.com execution history
- Monitor Google Sheets dashboard
- Keep local copy in sync with cloud
```

---

## 🔄 Weekly Workflow (After Go Live)

### Your Part
```
Monday:
  08:00 - Cloud pipeline auto-runs ✅
  08:15 - Check email for results
  Optional: Review Google Sheets dashboard
  Optional: Modify and re-deploy code

Tuesday-Sunday:
  Just monitor for alerts
```

### Supervisors' Part
```
Monday:
  08:15 - Receive email with results
  Optional: Click webhook to upload to WordPress
  Anytime: Check shared dashboard

Rest of week:
  Just view the calendar (events are published)
```

---

## 🆘 Troubleshooting

### Lambda won't run
```
1. Check Make.com execution history
2. Check AWS CloudWatch logs
3. Test code locally: python scripts/make_health_check.py
4. Re-deploy: make_deploy_helper.py --prepare
```

### Email not sending
```
1. Verify EMAIL_PASSWORD is Gmail App Password
2. Check SMTP_SERVER is smtp.gmail.com:587
3. Test: python scripts/make_health_check.py
```

### WordPress not updating
```
1. Run local test: python scripts/test_wp_auth.py
2. Verify App Password hasn't changed
3. Check REST API is enabled in WordPress
```

### Make.com can't reach Google Drive
```
1. Re-authorize: Connections → Google Drive
2. Verify folder permissions (not private)
3. Copy correct folder ID from Drive URL
```

---

## 📞 Support Chain

```
You (Admin)
├─ Can edit code and deploy
├─ Troubleshoot via AWS logs
└─ Contact: AWS support

Supervisors (Viewers)
├─ Can trigger uploads
├─ View dashboard
└─ Contact: You

External Issues
├─ Make.com down? → make.com/status
├─ AWS down? → status.aws.amazon.com
├─ WordPress down? → Your WordPress provider
└─ Gmail down? → Google status page
```

---

## 🎓 Learning Path

1. **Start**: Read MAKE_COM_MIGRATION_GUIDE.md (15 min)
2. **Understand**: Review MAKE_COM_ARCHITECTURE_REFERENCE.md (10 min)
3. **Do**: Follow MAKE_COM_QUICK_START_CHECKLIST.md daily (varies)
4. **Reference**: Use this card for quick lookup

---

## ✅ Success Indicators

You'll know it's working when:

- [ ] Pipeline runs Monday 8 AM automatically
- [ ] Supervisors receive email
- [ ] Google Drive has output CSV
- [ ] Health check passes all tests
- [ ] Google Sheets dashboard updates weekly
- [ ] Supervisors can click webhook to upload
- [ ] WordPress calendar has new events
- [ ] No manual intervention needed

---

## 🚀 You're Ready When

- [ ] Google Drive folder set up with model files
- [ ] Make.com account created
- [ ] AWS account created + CLI installed
- [ ] All 3 Python helper scripts understand
- [ ] Supervisor list ready
- [ ] WordPress credentials verified

**Then follow the Quick Start Checklist → PROFIT!**

---

## Command Cheat Sheet

```powershell
# View AWS Lambda logs
aws logs tail /aws/lambda/EnvisionPerdido-Pipeline --follow

# Redeploy code
python scripts/make_deploy_helper.py --prepare
aws lambda update-function-code `
  --function-name EnvisionPerdido-Pipeline `
  --zip-file fileb://lambda_deployment/lambda_function.zip

# Test health check
python scripts/make_health_check.py

# Run local pipeline
python scripts/automated_pipeline.py

# View available functions
aws lambda list-functions --query Functions[].FunctionName
```

---

## 📚 Full Documentation Structure

```
docs/
├── MAKE_COM_MIGRATION_GUIDE.md
│   └─ Complete 12-phase guide with all details
├── MAKE_COM_QUICK_START_CHECKLIST.md
│   └─ 20-day implementation checklist (USE THIS)
├── MAKE_COM_ARCHITECTURE_REFERENCE.md
│   └─ Architecture, costs, security, FAQs
└── MAKE_COM_DEPLOYMENT_PACKAGE_SUMMARY.md
    └─ Overview of entire package
```

---

## TL;DR (Ultra-Quick)

1. Create Google Drive folder + upload models
2. Run `python scripts/make_deploy_helper.py --all`
3. Deploy Lambda (copy/paste AWS CLI commands)
4. Add secrets to Make.com vault
5. Create 3 scenarios in Make.com
6. Test
7. Invite supervisors
8. Go live
9. Monitor

**Total time: 3-4 weeks**  
**Cost: $0**  
**Payoff: 24/7 automation**

---

## Questions?

- **About Make.com?** → https://www.make.com/en/help/
- **About AWS?** → https://docs.aws.amazon.com/
- **About the code?** → See scripts/ folder
- **About workflow?** → See MAKE_COM_MIGRATION_GUIDE.md

---

**Version**: 2.0 (Make.com Edition)  
**Status**: Ready to Deploy  
**Next Step**: Open MAKE_COM_MIGRATION_GUIDE.md & start Week 1!

🚀 Let's move to the cloud! 🚀
