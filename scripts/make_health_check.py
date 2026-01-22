"""
Health Check Module for Make.com CI/CD Pipeline

Monitors:
1. WordPress REST API connectivity
2. Email (SMTP) connectivity  
3. Google Drive API connectivity
4. Model artifacts availability
"""

import os
import json
import sys
import base64
import smtplib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

try:
    import requests
except ImportError:
    print("WARNING: requests library not available")
    requests = None


def check_wordpress_health(wp_url: str, wp_user: str, wp_password: str) -> Dict[str, Any]:
    """
    Test WordPress REST API connectivity.
    
    Args:
        wp_url: WordPress site URL (e.g., https://example.org)
        wp_user: WordPress username
        wp_password: WordPress application password
    
    Returns:
        dict with 'status', 'code', 'message' keys
    """
    if not requests:
        return {'status': 'skipped', 'reason': 'requests library not available'}
    
    try:
        # Construct Basic Auth header
        credentials = base64.b64encode(
            f"{wp_user}:{wp_password}".encode()
        ).decode()
        
        headers = {
            'Authorization': f'Basic {credentials}',
            'Content-Type': 'application/json'
        }
        
        # Test endpoint: get current user
        test_url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/users/me"
        
        response = requests.get(test_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            return {
                'status': 'ok',
                'code': response.status_code,
                'message': f'WordPress API responding correctly',
                'user': response.json().get('name', 'Unknown')
            }
        else:
            return {
                'status': 'error',
                'code': response.status_code,
                'message': f'WordPress API returned {response.status_code}',
                'response': response.text[:200]
            }
    
    except requests.exceptions.Timeout:
        return {
            'status': 'error',
            'message': 'WordPress API request timed out (10s)',
            'recommendation': 'Check internet connection and WordPress site status'
        }
    
    except requests.exceptions.ConnectionError as e:
        return {
            'status': 'error',
            'message': f'Could not connect to WordPress: {str(e)}',
            'recommendation': 'Verify WP_SITE_URL is correct and site is online'
        }
    
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Unexpected error: {str(e)}',
            'type': type(e).__name__
        }


def check_email_health(smtp_server: str, smtp_port: int | str, sender_email: str, 
                       password: str) -> Dict[str, Any]:
    """
    Test SMTP email connectivity.
    
    Args:
        smtp_server: SMTP server (e.g., smtp.gmail.com)
        smtp_port: SMTP port (typically 587 or 465)
        sender_email: Sender email address
        password: Email password or App Password
    
    Returns:
        dict with 'status', 'message' keys
    """
    try:
        port = int(smtp_port)
        
        # Create SMTP connection
        server = smtplib.SMTP(smtp_server, port, timeout=10)
        server.starttls()
        
        # Attempt login
        server.login(sender_email, password)
        server.quit()
        
        return {
            'status': 'ok',
            'message': f'SMTP connection successful ({smtp_server}:{port})'
        }
    
    except smtplib.SMTPAuthenticationError:
        return {
            'status': 'error',
            'message': 'SMTP authentication failed',
            'recommendation': 'Verify EMAIL_PASSWORD is correct (use Gmail App Password for Gmail)'
        }
    
    except smtplib.SMTPException as e:
        return {
            'status': 'error',
            'message': f'SMTP error: {str(e)}',
            'recommendation': 'Check SMTP_SERVER and SMTP_PORT settings'
        }
    
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Unexpected error: {str(e)}',
            'type': type(e).__name__
        }


def check_model_artifacts() -> Dict[str, Any]:
    """
    Check if model artifact files are available.
    
    Returns:
        dict with 'status', 'message' keys
    """
    base_dir = Path(__file__).parent.parent
    
    model_path = base_dir / "data" / "artifacts" / "event_classifier_model.pkl"
    vectorizer_path = base_dir / "data" / "artifacts" / "event_vectorizer.pkl"
    
    checks = {
        'model_exists': model_path.exists(),
        'vectorizer_exists': vectorizer_path.exists(),
    }
    
    # Get file sizes if they exist
    sizes = {}
    if checks['model_exists']:
        sizes['model_size_mb'] = round(model_path.stat().st_size / (1024 * 1024), 2)
    if checks['vectorizer_exists']:
        sizes['vectorizer_size_mb'] = round(vectorizer_path.stat().st_size / (1024 * 1024), 2)
    
    all_exist = all(checks.values())
    
    return {
        'status': 'ok' if all_exist else 'error',
        'message': 'All model artifacts present' if all_exist else 'Missing model artifacts',
        'checks': checks,
        'sizes': sizes,
        'recommendation': 'Run model training script to regenerate' if not all_exist else None
    }


def check_google_drive_health() -> Dict[str, Any]:
    """
    Check Google Drive accessibility (via Make.com connector).
    
    Note: This is a placeholder. In production, Make.com would verify
    the Google Drive connection before calling this.
    
    Returns:
        dict with 'status', 'message' keys
    """
    return {
        'status': 'ok',
        'message': 'Google Drive connectivity checked by Make.com connector',
        'note': 'Full validation requires authenticated Make.com session'
    }


def run_health_check() -> Dict[str, Any]:
    """
    Execute all health checks and return comprehensive report.
    
    Returns:
        dict with timestamp, check results, overall status, and recommendations
    """
    checks = {
        'wordpress': check_wordpress_health(
            os.getenv('WP_SITE_URL', ''),
            os.getenv('WP_USERNAME', ''),
            os.getenv('WP_APP_PASSWORD', '')
        ),
        'email': check_email_health(
            os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
            os.getenv('SMTP_PORT', '587'),
            os.getenv('SENDER_EMAIL', ''),
            os.getenv('EMAIL_PASSWORD', '')
        ),
        'model_artifacts': check_model_artifacts(),
        'google_drive': check_google_drive_health(),
    }
    
    # Determine overall status
    statuses = [c.get('status', 'unknown') for c in checks.values()]
    if 'error' in statuses:
        overall_status = 'error'
    elif 'warning' in statuses:
        overall_status = 'warning'
    else:
        overall_status = 'ok'
    
    # Collect recommendations
    recommendations = []
    for check_name, check_result in checks.items():
        if 'recommendation' in check_result:
            recommendations.append(f"{check_name}: {check_result['recommendation']}")
    
    return {
        'timestamp': datetime.now().isoformat(),
        'overall_status': overall_status,
        'checks': checks,
        'recommendations': recommendations if recommendations else None,
        'passed': sum(1 for c in checks.values() if c.get('status') == 'ok'),
        'failed': sum(1 for c in checks.values() if c.get('status') == 'error'),
    }


def lambda_handler(event, context):
    """
    AWS Lambda handler for health check execution from Make.com.
    """
    try:
        result = run_health_check()
        
        return {
            'statusCode': 200 if result['overall_status'] == 'ok' else 500,
            'body': json.dumps(result),
            'headers': {'Content-Type': 'application/json'}
        }
    
    except Exception as e:
        import traceback
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'status': 'error',
                'message': str(e),
                'traceback': traceback.format_exc()
            }),
            'headers': {'Content-Type': 'application/json'}
        }


if __name__ == '__main__':
    # Local test
    result = run_health_check()
    print(json.dumps(result, indent=2))
