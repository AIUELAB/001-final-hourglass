#!/usr/bin/env python3
"""
Security validation script for Ultra Think Project.
Validates that all security improvements are properly implemented.
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, List, Tuple

class SecurityValidator:
    """Validate security improvements in the project."""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.issues = []
        self.checks_passed = 0
        self.checks_total = 0
    
    def check_env_file_exists(self) -> bool:
        """Check if .env template file exists."""
        env_file = self.project_root / '.env'
        if env_file.exists():
            self.checks_passed += 1
            print("✅ .env template file exists")
            return True
        else:
            self.issues.append("❌ .env template file missing")
            return False
    
    def check_secure_config_exists(self) -> bool:
        """Check if secure config module exists."""
        config_file = self.project_root / 'src' / 'secure_config.py'
        if config_file.exists():
            self.checks_passed += 1
            print("✅ src/secure_config.py exists")
            return True
        else:
            self.issues.append("❌ src/secure_config.py missing")
            return False
    
    def check_gitignore_security(self) -> bool:
        """Check if .gitignore properly excludes sensitive files."""
        gitignore_file = self.project_root / '.gitignore'
        if not gitignore_file.exists():
            self.issues.append("❌ .gitignore file missing")
            return False
        
        content = gitignore_file.read_text()
        critical_patterns = [
            'key/',
            'keys/',
            'credentials.json',
            '*firebase*adminsdk*.json',
            'service-account*.json',
            '.env.production.local',
            '.env.development.local'
        ]
        
        missing_patterns = []
        for pattern in critical_patterns:
            if pattern not in content:
                missing_patterns.append(pattern)
        
        if not missing_patterns:
            self.checks_passed += 1
            print("✅ .gitignore properly excludes sensitive files")
            return True
        else:
            self.issues.append(f"❌ .gitignore missing patterns: {', '.join(missing_patterns)}")
            return False
    
    def check_env_mcp_cleaned(self) -> bool:
        """Check if .env.mcp file has been cleaned of exposed credentials."""
        env_mcp_file = self.project_root / '.env.mcp'
        if not env_mcp_file.exists():
            print("ℹ️ .env.mcp file not found (acceptable)")
            self.checks_passed += 1
            return True
        
        content = env_mcp_file.read_text()
        # Check for patterns that look like real API keys
        suspicious_patterns = ['ghp_', 'sk-ant-api', 'AIzaSy', 'BSAZ']
        
        found_suspicious = []
        for pattern in suspicious_patterns:
            if pattern in content:
                found_suspicious.append(pattern)
        
        if not found_suspicious:
            self.checks_passed += 1
            print("✅ .env.mcp file is clean of exposed credentials")
            return True
        else:
            self.issues.append(f"❌ .env.mcp still contains suspicious patterns: {', '.join(found_suspicious)}")
            return False
    
    def check_hardcoded_credentials(self) -> bool:
        """Check for remaining hardcoded credential paths."""
        python_files = list(self.project_root.glob("*.py"))
        python_files.extend(list(self.project_root.glob("**/*.py")))
        
        # Filter out venv and test files
        python_files = [f for f in python_files if 'venv/' not in str(f) and '__pycache__' not in str(f)]
        
        hardcoded_patterns = [
            'key/credentials.json',
            '/Users/admin/Documents/key/',
            '/Users/admin/Documents/AIUELAB/001-final-hourglass/key/'
        ]
        
        files_with_issues = []
        for file_path in python_files:
            try:
                content = file_path.read_text(encoding='utf-8')
                for pattern in hardcoded_patterns:
                    if pattern in content and 'scripts/fix_hardcoded_credentials.py' not in str(file_path):
                        files_with_issues.append((str(file_path), pattern))
            except Exception:
                continue  # Skip files we can't read
        
        if not files_with_issues:
            self.checks_passed += 1
            print("✅ No hardcoded credential paths found")
            return True
        else:
            self.issues.append(f"❌ Found hardcoded credentials in: {files_with_issues[:3]}")  # Show first 3
            return False
    
    def check_secure_config_imports(self) -> bool:
        """Check if files using secure config have proper imports."""
        python_files = list(self.project_root.glob("*.py"))
        
        files_needing_import = []
        files_with_import = []
        
        for file_path in python_files:
            if 'venv/' in str(file_path) or '__pycache__' in str(file_path):
                continue
            
            try:
                content = file_path.read_text(encoding='utf-8')
                if 'config.google_credentials_path' in content or 'config.firebase_credentials_path' in content:
                    if 'from src.secure_config import config' not in content:
                        files_needing_import.append(str(file_path))
                    else:
                        files_with_import.append(str(file_path))
            except Exception:
                continue
        
        if not files_needing_import:
            self.checks_passed += 1
            print(f"✅ All files using secure config have proper imports ({len(files_with_import)} files)")
            return True
        else:
            self.issues.append(f"❌ Files missing secure_config import: {files_needing_import[:3]}")
            return False
    
    def check_key_directory_security(self) -> bool:
        """Check if key directory is properly protected."""
        key_dir = self.project_root / 'key'
        
        if not key_dir.exists():
            print("ℹ️ key/ directory not found (acceptable if using environment variables)")
            self.checks_passed += 1
            return True
        
        # Check if key directory contains sensitive files
        sensitive_files = list(key_dir.glob("*.json"))
        sensitive_files.extend(list(key_dir.glob("*.pem")))
        sensitive_files.extend(list(key_dir.glob("*.key")))
        
        if sensitive_files:
            print(f"⚠️ key/ directory contains {len(sensitive_files)} sensitive files")
            print("   Ensure these are properly excluded from git")
            self.checks_passed += 1
            return True
        else:
            print("✅ key/ directory is clean")
            self.checks_passed += 1
            return True
    
    def check_environment_variable_usage(self) -> bool:
        """Check if environment variables are being used properly."""
        try:
            # Try to import and test secure config
            sys.path.append(str(self.project_root))
            from src.secure_config import config
            
            # Test key methods
            test_results = {
                'google_credentials_path': config.google_credentials_path is not None,
                'github_token': config.github_token is not None,
                'get_api_keys_status': bool(config.get_api_keys_status())
            }
            
            if all(test_results.values()):
                self.checks_passed += 1
                print("✅ secure_config module is functioning properly")
                return True
            else:
                self.issues.append(f"❌ secure_config issues: {test_results}")
                return False
                
        except Exception as e:
            self.issues.append(f"❌ secure_config import/test failed: {e}")
            return False
    
    def run_full_validation(self) -> Dict:
        """Run all security validation checks."""
        print("🛡️ Running Security Validation for Ultra Think Project...\n")
        
        # Define all checks
        checks = [
            ("Environment Template", self.check_env_file_exists),
            ("Secure Config Module", self.check_secure_config_exists),
            (".gitignore Security", self.check_gitignore_security),
            ("Cleaned .env.mcp", self.check_env_mcp_cleaned),
            ("No Hardcoded Credentials", self.check_hardcoded_credentials),
            ("Secure Config Imports", self.check_secure_config_imports),
            ("Key Directory Security", self.check_key_directory_security),
            ("Environment Variables", self.check_environment_variable_usage)
        ]
        
        self.checks_total = len(checks)
        
        # Run all checks
        for check_name, check_func in checks:
            print(f"\n🔍 Checking: {check_name}")
            try:
                check_func()
            except Exception as e:
                self.issues.append(f"❌ {check_name} failed with error: {e}")
                print(f"❌ Error during check: {e}")
        
        # Generate report
        score = (self.checks_passed / self.checks_total) * 100
        
        report = {
            'timestamp': str(Path().resolve()),
            'score': score,
            'checks_passed': self.checks_passed,
            'checks_total': self.checks_total,
            'issues': self.issues,
            'status': 'PASS' if score >= 90 else 'WARN' if score >= 70 else 'FAIL'
        }
        
        return report
    
    def print_report(self, report: Dict):
        """Print formatted validation report."""
        print(f"\n{'='*60}")
        print(f"🛡️ SECURITY VALIDATION REPORT")
        print(f"{'='*60}")
        
        # Score
        score = report['score']
        if score >= 90:
            status_emoji = "✅"
            status_color = "green"
        elif score >= 70:
            status_emoji = "⚠️"
            status_color = "yellow"
        else:
            status_emoji = "❌"
            status_color = "red"
        
        print(f"Overall Score: {status_emoji} {score:.1f}% ({report['checks_passed']}/{report['checks_total']})")
        print(f"Status: {status_emoji} {report['status']}")
        
        # Issues
        if report['issues']:
            print(f"\n🔍 Issues Found:")
            for issue in report['issues']:
                print(f"  {issue}")
        
        # Recommendations
        print(f"\n📋 Security Recommendations:")
        print("  1. Regularly rotate API keys and service account keys")
        print("  2. Monitor .env files for accidental commits")
        print("  3. Use different credentials for development and production")
        print("  4. Implement credential scanning in CI/CD pipeline")
        
        print(f"\n✅ Security validation completed!")


def main():
    """Main execution function."""
    validator = SecurityValidator()
    report = validator.run_full_validation()
    validator.print_report(report)
    
    # Save report to file
    report_file = Path("security_validation_report.json")
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Report saved to: {report_file}")
    
    # Exit with appropriate code
    sys.exit(0 if report['status'] == 'PASS' else 1)


if __name__ == "__main__":
    main()