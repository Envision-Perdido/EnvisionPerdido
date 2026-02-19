"""
Make.com Deployment Helper

This script helps prepare and deploy the EnvisionPerdido pipeline to AWS Lambda.

Usage:
    python scripts/make_deploy_helper.py --prepare  # Create lambda deployment package
    python scripts/make_deploy_helper.py --deploy    # Deploy to AWS (requires AWS CLI)
"""

import os
import sys
import shutil
import json
import argparse
from pathlib import Path
from datetime import datetime
import subprocess
import zipfile


class MakeDeployHelper:
    """Helper for Make.com deployment."""
    
    def __init__(self, base_dir=None):
        """Initialize deployment helper."""
        if base_dir is None:
            base_dir = Path(__file__).parent.parent
        
        self.base_dir = Path(base_dir)
        self.lambda_dir = self.base_dir / "lambda_deployment"
        self.requirements_file = self.base_dir / "requirements.txt"
        self.zip_file = self.lambda_dir / "lambda_function.zip"
    
    def prepare_lambda_package(self, clean=True):
        """
        Prepare deployment package for AWS Lambda.
        
        Args:
            clean (bool): If True, remove existing lambda_deployment directory
        """
        print("[INFO] Preparing Lambda deployment package...")
        
        # Clean up if requested
        if clean and self.lambda_dir.exists():
            print(f"[INFO] Removing old deployment directory: {self.lambda_dir}")
            shutil.rmtree(self.lambda_dir)
        
        # Create lambda directory
        self.lambda_dir.mkdir(exist_ok=True)
        print(f"[INFO] Created: {self.lambda_dir}")
        
        # Files to copy
        script_files = [
            'scripts/make_cloud_pipeline.py',
            'scripts/make_health_check.py',
            'scripts/automated_pipeline.py',
            'scripts/Envision_Perdido_DataCollection.py',
            'scripts/event_normalizer.py',
            'scripts/env_loader.py',
            'scripts/logger.py',
            'scripts/wordpress_uploader.py',
        ]
        
        # Copy scripts
        for script in script_files:
            src = self.base_dir / script
            if src.exists():
                # Create subdirectory if needed
                dst_dir = self.lambda_dir / 'scripts'
                dst_dir.mkdir(exist_ok=True)
                dst = dst_dir / src.name
                shutil.copy2(src, dst)
                print(f"[OK] Copied: {script}")
            else:
                print(f"[WARN] Not found: {script}")
        
        # Copy main module
        main_module = self.base_dir / 'Envision_Perdido_DataCollection.py'
        if main_module.exists():
            shutil.copy2(main_module, self.lambda_dir / main_module.name)
            print(f"[OK] Copied: {main_module.name}")
        
        # Copy requirements.txt
        if self.requirements_file.exists():
            shutil.copy2(self.requirements_file, self.lambda_dir / 'requirements.txt')
            print(f"[OK] Copied: requirements.txt")
        else:
            print("[WARN] requirements.txt not found")
        
        # Create lambda handler entry point
        handler_code = '''"""
AWS Lambda Entry Point for Make.com

Automatically generated handler that redirects to make_cloud_pipeline.
"""

import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent))

from scripts.make_cloud_pipeline import lambda_handler

# Lambda expects a handler function named 'lambda_handler'
__all__ = ['lambda_handler']
'''
        
        handler_file = self.lambda_dir / 'lambda_handler.py'
        handler_file.write_text(handler_code)
        print(f"[OK] Created: lambda_handler.py")
        
        # Install dependencies
        print("[INFO] Installing Python dependencies...")
        requirements = self.lambda_dir / 'requirements.txt'
        if requirements.exists():
            result = subprocess.run([
                sys.executable, '-m', 'pip', 'install',
                '-r', str(requirements),
                '-t', str(self.lambda_dir)
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("[OK] Dependencies installed")
            else:
                print(f"[ERROR] Dependency installation failed:")
                print(result.stderr)
                return False
        
        # Create ZIP file
        print("[INFO] Creating deployment ZIP...")
        self._create_zip()
        
        # Print summary
        zip_size = self.zip_file.stat().st_size / (1024 * 1024)
        print(f"\n[SUCCESS] Lambda package ready!")
        print(f"  File: {self.zip_file}")
        print(f"  Size: {zip_size:.2f} MB")
        
        if zip_size > 50:
            print(f"  [WARN] Package exceeds 50 MB limit. Consider removing unused dependencies.")
        
        return True
    
    def _create_zip(self):
        """Create ZIP file from lambda directory."""
        # Remove existing ZIP
        if self.zip_file.exists():
            self.zip_file.unlink()
        
        # Create ZIP
        with zipfile.ZipFile(self.zip_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in self.lambda_dir.rglob('*'):
                if file_path.is_file():
                    # Get relative path for archive
                    arcname = file_path.relative_to(self.lambda_dir)
                    zf.write(file_path, arcname)
                    print(f"  Added: {arcname}")
    
    def show_deploy_instructions(self):
        """Print AWS CLI deployment instructions."""
        print("\n" + "="*70)
        print("DEPLOYMENT INSTRUCTIONS (AWS CLI)")
        print("="*70 + "\n")
        
        print("1. Prerequisites:")
        print("   - AWS CLI installed: https://aws.amazon.com/cli/")
        print("   - AWS credentials configured: aws configure")
        print("   - AWS IAM Lambda execution role created\n")
        
        print("2. Create Lambda function (one-time):")
        print("""
aws lambda create-function \\
  --function-name EnvisionPerdido-Pipeline \\
  --runtime python3.11 \\
  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/lambda-execution-role \\
  --handler lambda_handler.lambda_handler \\
  --zip-file fileb://lambda_deployment/lambda_function.zip \\
  --timeout 300 \\
  --memory-size 512 \\
  --environment Variables="{AUTO_UPLOAD=false}"
        """)
        
        print("\n3. Create Function URL (for Make.com webhook):")
        print("""
aws lambda create-function-url-config \\
  --function-name EnvisionPerdido-Pipeline \\
  --auth-type NONE \\
  --cors AllowOrigins='*',AllowMethods='POST',AllowHeaders='*'
        """)
        
        print("\n4. Get Function URL:")
        print("""
aws lambda get-function-url-config --function-name EnvisionPerdido-Pipeline

# Copy the FunctionUrl - this is what you'll use in Make.com
        """)
        
        print("\n5. Update after code changes:")
        print("""
aws lambda update-function-code \\
  --function-name EnvisionPerdido-Pipeline \\
  --zip-file fileb://lambda_deployment/lambda_function.zip
        """)
        
        print("\n" + "="*70 + "\n")
    
    def create_secrets_template(self):
        """Create template files for secrets management."""
        print("[INFO] Creating secrets templates...")
        
        scripts_dir = self.base_dir / 'scripts'
        
        # Template (committed to git)
        template = {
            "DESCRIPTION": "Make.com Environment Variables Template",
            "REQUIRED_ENV_VARS": {
                "SMTP_SERVER": "smtp.gmail.com",
                "SMTP_PORT": "587",
                "SENDER_EMAIL": "your_email@gmail.com",
                "EMAIL_PASSWORD": "STORE_IN_MAKE_SECRETS",
                "RECIPIENT_EMAIL": "your_email@gmail.com",
                "WP_SITE_URL": "https://your-wordpress-site.org",
                "WP_USERNAME": "your_wp_username",
                "WP_APP_PASSWORD": "STORE_IN_MAKE_SECRETS",
                "GOOGLE_DRIVE_FOLDER_ID": "your_folder_id_here",
                "SITE_TIMEZONE": "America/Chicago"
            },
            "NOTES": [
                "Store all STORE_IN_MAKE_SECRETS values in Make.com Secrets vault",
                "Do NOT commit actual credentials to git",
                "Use make_env_template.json as reference only"
            ]
        }
        
        template_file = scripts_dir / 'make_env_template.json'
        template_file.write_text(json.dumps(template, indent=2))
        print(f"[OK] Created template: {template_file.name}")
        print(f"     Add to git (safe)")
        
        # Secrets file (not committed)
        secrets = {
            "SMTP_SERVER": "smtp.gmail.com",
            "SMTP_PORT": "587",
            "SENDER_EMAIL": "your_email@gmail.com",
            "EMAIL_PASSWORD": "your_16_char_app_password",
            "RECIPIENT_EMAIL": "supervisor@example.com",
            "WP_SITE_URL": "https://your-site.org",
            "WP_USERNAME": "your_wp_username",
            "WP_APP_PASSWORD": "xxxx xxxx xxxx xxxx xxxx xxxx",
            "GOOGLE_DRIVE_FOLDER_ID": "1abc2def3ghi4jkl5mno6pqr",
            "SITE_TIMEZONE": "America/Chicago"
        }
        
        secrets_file = scripts_dir / 'make_env_secrets.json'
        secrets_file.write_text(json.dumps(secrets, indent=2))
        print(f"[OK] Created secrets: {secrets_file.name}")
        print(f"     DO NOT add to git (listed in .gitignore)")
        
        # Update .gitignore
        gitignore_path = self.base_dir / '.gitignore'
        if gitignore_path.exists():
            content = gitignore_path.read_text()
            if 'make_env_secrets.json' not in content:
                content += '\n\n# Make.com deployment\nscripts/make_env_secrets.json\nlambda_deployment/\n'
                gitignore_path.write_text(content)
                print(f"[OK] Updated: .gitignore")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Make.com Deployment Helper for EnvisionPerdido'
    )
    
    parser.add_argument(
        '--prepare',
        action='store_true',
        help='Prepare Lambda deployment package'
    )
    parser.add_argument(
        '--deploy',
        action='store_true',
        help='Show deployment instructions (requires AWS CLI)'
    )
    parser.add_argument(
        '--secrets',
        action='store_true',
        help='Create secrets management templates'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Do all: prepare, show instructions, and create secrets'
    )
    
    args = parser.parse_args()
    
    helper = MakeDeployHelper()
    
    if args.all or args.prepare:
        helper.prepare_lambda_package()
    
    if args.all or args.secrets:
        helper.create_secrets_template()
    
    if args.all or args.deploy:
        helper.show_deploy_instructions()
    
    if not any([args.all, args.prepare, args.deploy, args.secrets]):
        parser.print_help()


if __name__ == '__main__':
    main()
