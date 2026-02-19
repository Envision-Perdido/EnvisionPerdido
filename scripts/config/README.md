# Configuration Files

Environment and deployment configuration templates.

## Files

- `make_env_secrets.json` — Example secrets (DO NOT COMMIT)
  - Template for environment variables passed to Lambda
  - Contains sensitive data (never commit to git)
  - Used for Make.com deployment or local testing
  - Copy and fill in with real values

- `make_env_template.json` — Configuration template
  - Describes required environment variables
  - Documents expected values and formats
  - Notes which variables should be stored in Make.com Secrets
  - Use as reference for setup

## Usage

### Local Testing
```bash
# Copy template and fill in values
cp config/make_env_template.json config/make_env_secrets.json

# Edit with real credentials
vim config/make_env_secrets.json

# Load into environment
export $(cat config/make_env_secrets.json | jq -r 'to_entries | .[] | "\(.key)=\(.value)"')
```

### AWS Lambda
```bash
# Option 1: Lambda environment variables
aws lambda update-function-configuration \
  --environment Variables={...}

# Option 2: Pass in HTTP request (via Make.com)
# Secrets sent in request body at runtime
```

### Make.com
```
1. Go to Make.com Scenario
2. Create "Secrets" data store
3. Add each secret as separate entry
4. Reference in HTTP module: {{secrets.WP_SITE_URL}}, etc.
5. Never hardcode credentials in WebAssembly code
```

## Security Best Practices

### DO NOT
- ❌ Commit `make_env_secrets.json` to git
- ❌ Hardcode credentials in code
- ❌ Share secrets in email or chat
- ❌ Use production credentials for testing

### DO
- ✅ Use `.gitignore` to exclude `make_env_secrets.json`
- ✅ Store secrets in AWS Secrets Manager or Make.com Secrets
- ✅ Rotate passwords and API keys regularly
- ✅ Use least-privilege AWS IAM roles
- ✅ Enable CloudTrail for audit logging

## Configuration Variables

### WordPress
```json
{
  "WP_SITE_URL": "https://example.org",
  "WP_USERNAME": "admin_user",
  "WP_APP_PASSWORD": "xxxx xxxx xxxx xxxx xxxx xxxx"
}
```

### Email/SMTP
```json
{
  "SMTP_SERVER": "smtp.gmail.com",
  "SMTP_PORT": "587",
  "SENDER_EMAIL": "sender@gmail.com",
  "EMAIL_PASSWORD": "16_character_app_password"
}
```

### Recipients
```json
{
  "RECIPIENT_EMAIL": "admin@example.org",
  "NOTIFY_EMAIL": "admin@example.org"
}
```

### Optional
```json
{
  "GOOGLE_DRIVE_FOLDER_ID": "1AV4jSzgjFkwC-FF_..."
}
```

### Behavior
```json
{
  "SITE_TIMEZONE": "America/Chicago",
  "AUTO_UPLOAD": "false"
}
```

## Gitignore

Add to `.gitignore`:
```
scripts/config/make_env_secrets.json
scripts/config/*.secrets.*
.env
.env.local
```

Ensure this is committed to prevent accidental credential leaks.
