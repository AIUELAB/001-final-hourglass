"""
Secure configuration management for Ultra Think Project.
Handles environment variables and credential loading safely.
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from google.oauth2 import service_account
from google.auth.credentials import Credentials

logger = logging.getLogger(__name__)


class SecureConfig:
    """Secure configuration manager for credentials and environment variables."""
    
    def __init__(self):
        """Initialize secure configuration with environment variable validation."""
        self._load_environment()
        self._validate_required_vars()
    
    def _load_environment(self) -> None:
        """Load environment variables from .env file if it exists."""
        env_file = Path(__file__).parent.parent / '.env'
        if env_file.exists():
            try:
                with open(env_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            os.environ.setdefault(key.strip(), value.strip())
            except Exception as e:
                logger.warning(f"Failed to load .env file: {e}")
    
    def _validate_required_vars(self) -> None:
        """Validate that required environment variables are present."""
        required_vars = [
            'GOOGLE_APPLICATION_CREDENTIALS',
            'GITHUB_TOKEN'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not self.get_env(var):
                missing_vars.append(var)
        
        if missing_vars:
            logger.warning(f"Missing environment variables: {', '.join(missing_vars)}")
    
    @staticmethod
    def get_env(key: str, default: Optional[str] = None) -> Optional[str]:
        """Safely get environment variable with optional default."""
        value = os.getenv(key, default)
        if value and value.lower() in ('none', 'null', ''):
            return None
        return value
    
    @property
    def google_credentials_path(self) -> Optional[str]:
        """Get Google credentials file path."""
        path = self.get_env('GOOGLE_APPLICATION_CREDENTIALS')
        if path and Path(path).exists():
            return path
        
        # Fallback to project-relative path
        fallback_path = Path(__file__).parent.parent / 'key' / 'credentials.json'
        if fallback_path.exists():
            return str(fallback_path)
        
        return None
    
    @property
    def firebase_credentials_path(self) -> Optional[str]:
        """Get Firebase credentials file path."""
        path = self.get_env('FIREBASE_CONFIG_PATH')
        if path and Path(path).exists():
            return path
        
        # Fallback patterns for Firebase credentials
        project_root = Path(__file__).parent.parent
        firebase_patterns = [
            'key/final-hourglass-claude-firebase-adminsdk-*.json',
            'key/*firebase*.json'
        ]
        
        for pattern in firebase_patterns:
            firebase_files = list(project_root.glob(pattern))
            if firebase_files:
                return str(firebase_files[0])
        
        return None
    
    def get_google_credentials(self) -> Optional[Credentials]:
        """Get Google service account credentials safely."""
        creds_path = self.google_credentials_path
        if not creds_path:
            logger.error("Google credentials file not found")
            return None
        
        try:
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive.file'
            ]
            credentials = service_account.Credentials.from_service_account_file(
                creds_path, scopes=scopes
            )
            return credentials
        except Exception as e:
            logger.error(f"Failed to load Google credentials: {e}")
            return None
    
    def get_firebase_credentials(self):
        """Get Firebase credentials safely."""
        creds_path = self.firebase_credentials_path
        if not creds_path:
            logger.error("Firebase credentials file not found")
            return None
        
        try:
            from firebase_admin import credentials
            return credentials.Certificate(creds_path)
        except ImportError:
            logger.error("firebase_admin not installed")
            return None
        except Exception as e:
            logger.error(f"Failed to load Firebase credentials: {e}")
            return None
    
    @property
    def github_token(self) -> Optional[str]:
        """Get GitHub token safely."""
        return self.get_env('GITHUB_TOKEN') or self.get_env('GITHUB_PAT')
    
    @property
    def anthropic_api_key(self) -> Optional[str]:
        """Get Anthropic API key safely."""
        return self.get_env('ANTHROPIC_API_KEY')
    
    @property
    def openai_api_key(self) -> Optional[str]:
        """Get OpenAI API key safely."""
        return self.get_env('OPENAI_API_KEY')
    
    @property
    def youtube_api_key(self) -> Optional[str]:
        """Get YouTube API key safely."""
        return self.get_env('YOUTUBE_API_KEY')
    
    @property
    def brave_api_key(self) -> Optional[str]:
        """Get Brave API key safely."""
        return self.get_env('BRAVE_API_KEY')
    
    def get_api_keys_status(self) -> Dict[str, bool]:
        """Get status of all API keys for health checks."""
        return {
            'google_credentials': self.google_credentials_path is not None,
            'firebase_credentials': self.firebase_credentials_path is not None,
            'github_token': self.github_token is not None,
            'anthropic_api_key': self.anthropic_api_key is not None,
            'openai_api_key': self.openai_api_key is not None,
            'youtube_api_key': self.youtube_api_key is not None,
            'brave_api_key': self.brave_api_key is not None,
        }
    
    def validate_credentials(self) -> Dict[str, Any]:
        """Validate all credentials and return detailed status."""
        status = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'credentials': {}
        }
        
        # Check Google credentials
        try:
            google_creds = self.get_google_credentials()
            status['credentials']['google'] = google_creds is not None
            if not google_creds:
                status['errors'].append("Google credentials not available")
                status['valid'] = False
        except Exception as e:
            status['errors'].append(f"Google credentials error: {e}")
            status['valid'] = False
        
        # Check Firebase credentials
        try:
            firebase_creds = self.get_firebase_credentials()
            status['credentials']['firebase'] = firebase_creds is not None
            if not firebase_creds:
                status['warnings'].append("Firebase credentials not available")
        except Exception as e:
            status['warnings'].append(f"Firebase credentials warning: {e}")
        
        # Check API keys
        api_keys = self.get_api_keys_status()
        status['credentials'].update(api_keys)
        
        missing_critical = []
        if not api_keys.get('github_token'):
            missing_critical.append('GitHub token')
        
        if missing_critical:
            status['errors'].extend([f"Missing critical credential: {cred}" for cred in missing_critical])
            status['valid'] = False
        
        return status


# Global configuration instance
config = SecureConfig()