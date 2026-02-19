# Deployment & Cloud Integration

Make.com (CloudMIG) deployment and AWS Lambda support.

## Scripts (3)

- `make_cloud_pipeline.py` — AWS Lambda entry point for Make.com
  - Designed to run on AWS Lambda via Make.com HTTP module
  - Loads secrets from Lambda event
  - Runs classification pipeline
  - Uploads results to Google Drive
  - Sends status emails
  - Returns structured results to Make.com
  - Handles environment setup and error reporting

- `make_deploy_helper.py` — AWS Lambda deployment preparation
  - Creates Lambda deployment package (.zip)
  - Bundles code with required dependencies
  - Generates deployment instructions
  - Creates secrets management templates
  - Validates package size and structure
  - Provides AWS CLI commands for deployment

- `make_health_check.py` — CI/CD health verification
  - Tests WordPress REST API connectivity
  - Validates SMTP email connectivity
  - Checks Google Drive API access
  - Verifies model artifacts availability
  - Returns structured health status
  - Used in CI/CD pipelines

## Workflow

### Local Development
```bash
# 1. Prepare deployment package
python deployment/make_deploy_helper.py --prepare

# 2. Review secrets template
cat deployment/config/make_env_secrets.json

# 3. Get deployment instructions
python deployment/make_deploy_helper.py --deploy
```

### AWS Lambda Deployment
```bash
# 1. Create Lambda function
aws lambda create-function \
  --function-name EnvisionPerdidoPipeline \
  --zip-file fileb://lambda_deploy.zip \
  --handler make_cloud_pipeline.lambda_handler \
  --runtime python3.11 \
  --role arn:aws:iam::ACCOUNT:role/lambda-role

# 2. Set Lambda environment variables (or pass in event)
aws lambda update-function-configuration \
  --function-name EnvisionPerdidoPipeline \
  --environment Variables={...}
```

### Make.com Integration
1. Create HTTP module in Make scenario
2. Set URL to Lambda function
3. Pass secrets in HTTP request body:
```json
{
  "WP_SITE_URL": "https://example.org",
  "WP_USERNAME": "user",
  "WP_APP_PASSWORD": "xxxx xxxx xxxx xxxx",
  "SMTP_SERVER": "smtp.gmail.com",
  "SMTP_PORT": "587",
  "SENDER_EMAIL": "email@gmail.com",
  "EMAIL_PASSWORD": "16char_app_password",
  "SITE_TIMEZONE": "America/Chicago"
}
```

## Lambda Handler

```python
from deployment.make_cloud_pipeline import lambda_handler

# AWS Lambda calls this function
response = lambda_handler({
    "WP_SITE_URL": "...",
    "WP_USERNAME": "...",
    # ... more secrets
}, context)

# Returns:
{
  "statusCode": 200,
  "body": {
    "status": "success",
    "events_scraped": 42,
    "events_classified": 38,
    "events_exported": 35,
    "message": "Pipeline completed successfully"
  }
}
```

## Configuration Files

Located in `config/`:
- `make_env_secrets.json` — Example secrets (DO NOT COMMIT)
- `make_env_template.json` — Template for required variables

## Secrets Management

### AWS Lambda
- Use Lambda environment variables for non-sensitive config
- Use AWS Secrets Manager for passwords and API keys
- Or pass secrets in HTTP request (Make.com → Lambda)

### Make.com
- Store secrets in Make.com Secrets data store
- Reference via `{{secrets.VARIABLE_NAME}}`
- Never hardcode credentials in scenario

### Local Development
- Use `scripts/config/make_env_secrets.json` (git-ignored)
- Or set environment variables before running
- Or pass to Lambda via event for testing

## Deployment Package

The Lambda deployment package includes:
```
lambda_deploy.zip
├── make_cloud_pipeline.py (main handler)
├── make_health_check.py
├── core/ (utility modules)
├── ml/ (ML scripts)
├── data_processing/ (processing scripts)
├── scrapers/ (scraper modules)
├── bin/ (Python executable)
└── lib/ (dependencies: pandas, requests, scikit-learn, etc.)
```

Package size: ~150-200 MB (depending on dependencies)

## Monitoring & Alerts

Health checks run:
- On Lambda cold starts
- In CI/CD before deployment
- On Make.com scenario trigger
- Scheduled via CloudWatch Events

Alerts sent via email on:
- API connectivity failures
- SMTP configuration issues
- Missing model artifacts
- Google Drive access problems

## Performance Considerations

Lambda optimization:
- Function timeout: 15-30 minutes (configurable)
- Memory: 3 GB recommended (impacts CPU/network)
- Ephemeral storage: 10 GB (for temp files)
- Concurrent executions: Configure as needed

For large calendars (>1000 events):
- May need extended timeout
- Consider parallel uploads
- Monitor Lambda logs in CloudWatch

## Troubleshooting

Common issues:
- Missing dependencies → Rebuild Lambda package with `make_deploy_helper.py`
- Authentication errors → Check Make.com secrets configuration
- Timeout → Increase Lambda timeout or optimize processing
- Cold starts → Use Lambda Provisioned Concurrency

Check logs in CloudWatch:
```bash
aws logs tail /aws/lambda/EnvisionPerdidoPipeline --follow
```
