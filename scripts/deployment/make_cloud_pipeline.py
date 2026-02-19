"""
Make.com Cloud Pipeline Wrapper

This script is designed to run on AWS Lambda (via Make.com HTTP module).
It handles:
1. Loading secrets from Lambda event
2. Running the classification pipeline
3. Uploading results to Google Drive
4. Sending status emails
5. Returning structured results to Make.com
"""

import os
import json
import sys
import base64
from pathlib import Path
from datetime import datetime
import traceback

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def setup_environment(secrets):
    """
    Configure environment variables from secrets passed by Make.com.
    
    Args:
        secrets (dict): Environment variables passed by Make.com
    
    Returns:
        dict: Validated secrets
    """
    required_vars = [
        'SMTP_SERVER', 'SMTP_PORT', 'SENDER_EMAIL', 'EMAIL_PASSWORD',
        'RECIPIENT_EMAIL', 'WP_SITE_URL', 'WP_USERNAME', 'WP_APP_PASSWORD',
        'SITE_TIMEZONE'
    ]
    
    for var in required_vars:
        if var not in secrets or not secrets[var]:
            raise ValueError(f"Missing required secret: {var}")
        os.environ[var] = str(secrets[var])
    
    return secrets


def lambda_handler(event, context):
    """
    AWS Lambda handler for Make.com pipeline execution.
    
    This function is the entry point when called from Make.com.
    
    Args:
        event (dict): Lambda event containing:
            - SMTP_SERVER, SMTP_PORT, SENDER_EMAIL, EMAIL_PASSWORD
            - RECIPIENT_EMAIL, WP_SITE_URL, WP_USERNAME, WP_APP_PASSWORD
            - SITE_TIMEZONE
            - SKIP_WP_UPLOAD (optional): If 'true', skip WordPress upload
        
        context (object): Lambda context (not used)
    
    Returns:
        dict: Response with statusCode and body (JSON)
    """
    try:
        print("[INFO] Starting Make.com Cloud Pipeline")
        print(f"[INFO] Timestamp: {datetime.now().isoformat()}")
        
        # Setup environment
        secrets = setup_environment(event)
        print("[INFO] Environment configured")
        
        # Import pipeline modules (after env is set)
        from scripts import automated_pipeline
        
        # Run pipeline
        skip_upload = event.get('SKIP_WP_UPLOAD', 'false').lower() == 'true'
        print(f"[INFO] Skip WordPress upload: {skip_upload}")
        
        result = automated_pipeline.run_full_pipeline(skip_upload=skip_upload)
        
        response = {
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'data': result,
            'message': f"Pipeline completed successfully. "
                      f"{result.get('events_classified', 0)} events classified, "
                      f"{result.get('community_events', 0)} marked as community events."
        }
        
        print(f"[SUCCESS] {response['message']}")
        
        return {
            'statusCode': 200,
            'body': json.dumps(response),
            'headers': {'Content-Type': 'application/json'}
        }
    
    except Exception as e:
        error_msg = str(e)
        stack_trace = traceback.format_exc()
        
        print(f"[ERROR] Pipeline failed: {error_msg}")
        print(f"[DEBUG] {stack_trace}")
        
        response = {
            'status': 'error',
            'timestamp': datetime.now().isoformat(),
            'error': error_msg,
            'traceback': stack_trace
        }
        
        return {
            'statusCode': 500,
            'body': json.dumps(response),
            'headers': {'Content-Type': 'application/json'}
        }


def make_handler(event, context):
    """
    Alternative handler name for Make.com compatibility.
    Some deployments use different naming conventions.
    """
    return lambda_handler(event, context)


# For local testing without AWS
if __name__ == '__main__':
    # Test event
    test_event = {
        'SMTP_SERVER': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
        'SMTP_PORT': os.getenv('SMTP_PORT', '587'),
        'SENDER_EMAIL': os.getenv('SENDER_EMAIL'),
        'EMAIL_PASSWORD': os.getenv('EMAIL_PASSWORD'),
        'RECIPIENT_EMAIL': os.getenv('RECIPIENT_EMAIL'),
        'WP_SITE_URL': os.getenv('WP_SITE_URL'),
        'WP_USERNAME': os.getenv('WP_USERNAME'),
        'WP_APP_PASSWORD': os.getenv('WP_APP_PASSWORD'),
        'SITE_TIMEZONE': os.getenv('SITE_TIMEZONE', 'America/Chicago'),
        'SKIP_WP_UPLOAD': 'true'  # Safe for local testing
    }
    
    class FakeContext:
        pass
    
    result = lambda_handler(test_event, FakeContext())
    print(json.dumps(json.loads(result['body']), indent=2))
